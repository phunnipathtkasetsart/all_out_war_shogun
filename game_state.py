"""
game_state.py  –  Central game state shared across all modules.
"""
from clans import make_clans
from city import make_city, CITY_NAMES
from map import PROVINCE_POSITIONS, CLAN_STARTS, MapArmy
from forest import make_forest_points, check_ambush, AmbushEvent
from stats import StatsLogger
import random


class GameState:
    def __init__(self, player_clan_name: str):
        self.player_clan_name = player_clan_name
        self.turn = 1
        self.game_over = False
        self.winner = None
        self.log_messages = []     # recent event log for UI
        self.data_log = []         # per-turn CSV data
        self.clans = make_clans()
        self.cities = {}
        clan_provinces = {v: k for k, v in CLAN_STARTS.items()}

        for prov in PROVINCE_POSITIONS:
            owner = clan_provinces.get(prov, "Neutral")
            gdmg = self.clans[owner].default_dmg if owner in self.clans else 3.0
            self.cities[prov] = make_city(
                name=random.choice(CITY_NAMES),
                owner=owner,
                level=1,
                garrison_dmg=gdmg,
            )
        self.armies = []
        for clan_name, clan in self.clans.items():
            start_prov = CLAN_STARTS[clan_name]
            soldier = clan.spawn_default_soldier()
            army = MapArmy(clan_name, start_prov, [soldier])
            army.remaining_km = army.turn_km_budget()
            self.armies.append(army)
        self.forests: dict = make_forest_points()
        self.stats = StatsLogger(save_dir="saves")
        self._turn_start_time_real = __import__('time').time()
        self.pending_ambush: AmbushEvent | None = None
        self.selected_army = None       
        self.selected_province = None   
        self.highlighted_provinces = []  
        self.highlighted_armies    = []  

    # ── Helpers ───────────────────────────────────────────────────────────────

    def player_clan(self):
        return self.clans[self.player_clan_name]

    def log(self, message: str):
        self.log_messages.append(message)
        if len(self.log_messages) > 8:
            self.log_messages.pop(0)
        print(message)

    def get_armies_at(self, province: str) -> list:
        return [a for a in self.armies if a.province == province and a.is_alive()]

    def get_player_armies(self) -> list:
        return [a for a in self.armies if a.owner == self.player_clan_name and a.is_alive()]

    def clean_dead_armies(self):
        self.armies = [a for a in self.armies if a.is_alive()]

    def check_clan_elimination(self):
        for clan_name, clan in self.clans.items():
            if not clan.is_alive:
                continue
            owned = [p for p, c in self.cities.items() if c.owner == clan_name]
            lost  = [p for p in clan.territories if p not in owned]
            clan.territories = owned

            # Queue retake marches for any lost provinces
            for prov in lost:
                self._queue_retake(clan_name, prov)

            if len(owned) == 0:
                clan.is_alive = False
                self.log(f"{clan_name} has been eliminated!")
                self.armies = [a for a in self.armies if a.owner != clan_name]

        # Win condition
        all_owned = all(c.owner == self.player_clan_name for c in self.cities.values())
        if all_owned:
            self.game_over = True
            self.winner = self.player_clan_name
            self.log(f"🎌 {self.player_clan_name} has conquered Japan! YOU WIN!")

        # Loss condition
        player_clan = self.player_clan()
        if not player_clan.is_alive:
            self.game_over = True
            self.winner = "Enemy"
            self.log("Your clan has been eliminated. GAME OVER.")

    def _resolve_player_siege(self, army, target_prov):
        from combat import resolve_siege
        city = self.cities.get(target_prov)
        if not city or city.owner == self.player_clan_name or city.owner == "Neutral":
            army.siege_target = None
            return

        old_owner = city.owner
        new_dmg   = self.clans[army.owner].default_dmg if army.owner in self.clans else 3.0
        defending = [a for a in self.armies
                     if a.province == target_prov
                     and a.owner != army.owner
                     and a.is_alive()]
        if defending:
            self.log(f"Siege of {target_prov}: {len(defending)} enemy army/armies defending!")

        result = resolve_siege(army, city,
                               province_key=target_prov,
                               new_garrison_dmg=new_dmg,
                               defending_armies=defending)
        army.siege_target = None

        if result.get("attacker_wins"):
            old_clan = self.clans.get(old_owner)
            if old_clan and target_prov in old_clan.territories:
                old_clan.territories.remove(target_prov)
            if target_prov not in self.player_clan().territories:
                self.player_clan().territories.append(target_prov)
            army.exhaust(siege=True)
            self.log(f"Conquered {target_prov} from {old_owner}! "
                     f"(ATK {int(result['attacker_power'])} vs "
                     f"DEF {int(result['defender_power'])}) — Army exhausted.")
            self.stats.log(self.turn, "SIEGE_WIN", self.player_clan_name,
                           province=target_prov,
                           units=int(result.get("defender_power", 0)),
                           damage=int(result.get("attacker_power", 0)),
                           units_lost=int(result.get("attacker_lost", 0)),
                           provinces=len(self.player_clan().territories))
        else:
            self.log(f"Siege of {target_prov} failed — "
                     f"ATK {int(result['attacker_power'])} vs "
                     f"DEF {int(result['defender_power'])}. Recruit more soldiers.")
            self.stats.log(self.turn, "SIEGE_LOSS", self.player_clan_name,
                           province=target_prov,
                           units=int(result.get("defender_power", 0)),
                           damage=int(result.get("attacker_power", 0)),
                           units_lost=int(result.get("attacker_lost", 0)),
                           provinces=len(self.player_clan().territories))
        self.clean_dead_armies()
        self.check_clan_elimination()

    def _queue_retake(self, clan_name: str, lost_prov: str):
        clan = self.clans.get(clan_name)
        if not clan or not clan.is_alive:
            return

        # Mark the clan's retake target so AI prioritises it
        clan.retake_target = lost_prov

        # Find all surviving armies of this clan
        own_armies = [a for a in self.armies
                      if a.owner == clan_name and a.is_alive()]

        if not own_armies:
            self.log(f"{clan_name} lost {lost_prov} — no armies to retake, will recruit.")
            return

        # Queue march toward lost province for the strongest army
        strongest = max(own_armies, key=lambda a: a.total_power())

        def passable(p):
            city = self.cities.get(p)
            if city is None:
                return True
            return city.owner == clan_name or city.owner == "Neutral" or p == lost_prov

        ok = strongest.set_march_destination(lost_prov, passable_fn=passable)
        if ok:
            self.log(f"{clan_name} lost {lost_prov} — marching to retake! "
                     f"({strongest.turns_to_arrive()} turns away)")

    def end_turn(self):
        from ai import AIController

        for fp in self.forests.values():
            for army in list(fp.armies):
                if fp.should_auto_exit(army):
                    fp.exit(army)

        player = self.player_clan()
        for army in self.get_player_armies():
            if not army.is_marching():
                if army.siege_target and army.province == army.siege_target:
                    self._resolve_player_siege(army, army.siege_target)
                continue
            if army.next_province and not army.exhausted:
                amb = check_ambush(army, self)
                if amb:
                    if army.owner == self.player_clan_name:
                        self.pending_ambush = amb
                        # Snapshot units before resolve so we can compute losses
                        player_units_before  = army.total_units()
                        enemy_units_before   = sum(a.total_units() for a in amb.ambushers)
                        amb.resolve_fight(self)
                        # Compute own lost and enemy killed from the snapshots
                        player_units_after = army.total_units()
                        enemy_units_after  = sum(a.total_units() for a in amb.ambushers
                                                 if a.is_alive())
                        own_lost     = max(0, player_units_before - player_units_after)
                        enemy_killed = max(0, enemy_units_before  - enemy_units_after)
                        still_alive  = army.is_alive()
                        evt = "AMBUSH_LOSS" if not still_alive else "AMBUSH_WIN"
                        self.stats.log(self.turn, evt, self.player_clan_name,
                                       province=army.province,
                                       units=int(own_lost),      # ambush: use unit losses as power proxy
                                       damage=int(enemy_killed),
                                       units_lost=int(own_lost),
                                       provinces=len(self.player_clan().territories))
                    else:
                        amb.resolve_fight(self)

            entered = army.advance_turn()
            for prov in entered:
                city = self.cities.get(prov)
                if city and city.owner == "Neutral":
                    city.owner = self.player_clan_name
                    city.garrison.owner = self.player_clan_name
                    if prov not in player.territories:
                        player.territories.append(prov)
                    army.siege_target = None
                    army.exhaust(siege=False)
                    self.log(f"Claimed neutral province {prov}!")
                    break
                # If army reached its siege_target province — auto-siege
                elif prov == army.siege_target and not army.is_marching():
                    self._resolve_player_siege(army, prov)
                    break
                elif army.is_marching():
                    dest = army.march_queue[-1] if army.march_queue else (army.next_province or prov)
                    siege_note = f" [Sieging {army.siege_target}]" if army.siege_target else ""
                    self.log(f"Army marching → {dest}{siege_note}. "
                             f"{army.turns_to_arrive()} turn(s) remaining.")

        # ── 2. Tick production queues for all player cities ───────────────────
        for prov, city in self.cities.items():
            if city.owner != self.player_clan_name:
                continue
            ready = city.tick_queues()
            for soldier in ready:
                # Spawn completed soldier as a new army at that province
                existing = [a for a in self.armies
                            if a.owner == self.player_clan_name
                            and a.province == prov and a.is_alive()]
                if existing:
                    existing[0].soldiers.append(soldier)
                    self.log(f"✓ {soldier.name} trained at {prov} — joined existing army.")
                else:
                    from map import MapArmy
                    new_army = MapArmy(self.player_clan_name, prov, [soldier])
                    new_army.remaining_km = new_army.turn_kb_budget()  if False else new_army.turn_km_budget()
                    self.armies.append(new_army)
                    self.log(f"✓ {soldier.name} trained at {prov} — new army spawned.")
                # Log RECRUIT event
                self.stats.log(self.turn, "RECRUIT", self.player_clan_name,
                               province=prov, units=soldier.unit,
                               provinces=len(self.player_clan().territories))
            if city.upgrade_turns_left == 0 and city.city_level > 1:
                pass  # upgrade already fired inside tick_queues

        # ── 3. Player economy ─────────────────────────────────────────────────
        total_tax = 0
        for prov in list(self.cities.keys()):
            city = self.cities[prov]
            if city.owner == self.player_clan_name:
                total_tax += city.tax_income()
                result = city.rage_tax_calc(is_player=True)
                if result == "rebellion":
                    rebel_name = city.name
                    city.on_rebelled()
                    if prov in player.territories:
                        player.territories.remove(prov)
                    # Cancel any army (including player's) that was sieging this province
                    for a in self.armies:
                        if getattr(a, 'siege_target', None) == prov:
                            a.siege_target = None
                            a.cancel_march()
                    self.log(f"🔥 REBELLION in {rebel_name} ({prov})! City lost to rebels!")
                    self.stats.log(self.turn, "REBELLION", self.player_clan_name,
                                   province=prov, units=0,
                                   provinces=len(self.player_clan().territories))
                elif result and result.startswith("warning_"):
                    turns_left = result.split("_")[1]
                    resistance_note = " [Resistance to invaders!]" if city.resistance_turns > 0 else ""
                    self.log(f"⚠ {prov} — rebellion imminent in {turns_left} turn(s)!"
                             f"{resistance_note} Lower taxes or station more troops!")
                elif city.resistance_turns > 0:
                    # Still in resistance period — notify player once per turn
                    self.log(f"⚔ {prov}: resistance to invaders — {city.resistance_turns} turn(s) of unrest remaining.")

        player.collect_tax(total_tax)

        # ── Maintenance: unit * 10 gold per unit across ALL player armies ──────
        player_upkeep = sum(
            a.maintenance_cost()
            for a in self.armies
            if a.owner == self.player_clan_name and a.is_alive()
        )
        player.gold -= player_upkeep
        if player.gold < 0:
            player.debt = abs(player.gold)
            self.log(f"⚠ In debt! Upkeep {player_upkeep}G exceeds treasury. "
                     f"Cannot recruit or upgrade until debt is cleared.")
        else:
            player.debt = 0
            self.log(f"Tax +{total_tax}G | Upkeep -{player_upkeep}G | "
                     f"Treasury {player.gold}G")

        # ── 3. Reset player army action flags ─────────────────────────────────
        for army in self.get_player_armies():
            army.reset_turn()

        # ── 4. AI turns ───────────────────────────────────────────────────────
        ai = AIController(self)
        ai.run_enemy_turns()

        # ── 5. Rage/tax for enemy cities (skip Neutral and already-Rebels) ──────
        for prov, city in list(self.cities.items()):
            owner = city.owner
            # Only run rage for cities owned by AI clans (not player, not Neutral, not Rebels)
            if owner == self.player_clan_name or owner == "Neutral" or owner == "Rebels":
                continue
            result = city.rage_tax_calc()
            if result == "rebellion":
                city.on_rebelled()
                clan = self.clans.get(owner)
                if clan and prov in clan.territories:
                    clan.territories.remove(prov)
                # Cancel any army (player or AI) sieging this province
                for a in self.armies:
                    if getattr(a, 'siege_target', None) == prov:
                        a.siege_target = None
                        a.cancel_march()
                self.log(f"🔥 REBELLION in {prov} — {owner} loses {city.name}!")
            elif result and result.startswith("warning_"):
                turns_left = result.split("_")[1]
                self.log(f"⚠ {owner}: {prov} rebellion in {turns_left} turn(s)!")

        self.check_clan_elimination()

        # Log TURN_SNAPSHOT for all alive clans
        for cname, clan in self.clans.items():
            total_pw = sum(a.total_power() for a in self.armies
                           if a.owner == cname and a.is_alive())
            self.stats.log(self.turn, "TURN_SNAPSHOT", cname,
                           province="", units=int(total_pw),
                           provinces=len(clan.territories))
        self.stats.save()
        self.stats.reset_turn_timer()

        self.turn += 1
        self.log(f"── Turn {self.turn} ──")
        self._record_turn_data()

    def _record_turn_data(self):
        player = self.player_clan()
        entry = {
            "turn": self.turn,
            "gold": player.gold,
            "territories": len(player.territories),
            "total_soldiers": sum(a.total_units() for a in self.get_player_armies()),
            "total_power": sum(a.total_power() for a in self.get_player_armies()),
        }
        self.data_log.append(entry)