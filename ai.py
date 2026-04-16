"""
ai.py  –  Aggressive AI.

Key behaviours:
  - EVERY army acts every turn — marching armies also attack if they pass an enemy
  - Siege threshold lowered to 0.30 (will attempt even losing fights to soften)
  - Attacks at 0.25 win_prob (always pressures)
  - Target reassessed every turn — always picks the best current opportunity
  - Armies don't over-consolidate — split between offence and home defence
  - Neutrals captured aggressively (no penalty)
  - Marching armies siege/attack any province they arrive at
  - Difficulty bonus every 3 turns (was 5)
"""
import random
from map import bfs_path, get_neighbors, MapArmy, TERRAIN, PROVINCE_POSITIONS
from combat import resolve_battle, resolve_siege, group_power
from city import CITY_LEVEL_CONFIG

# ── Tuning ────────────────────────────────────────────────────────────────────
WIN_PROB_ATTACK  = 0.25   # attack field army at this prob (very aggressive)
WIN_PROB_SIEGE   = 0.30   # siege city at this prob
WIN_PROB_CHIP    = 0.15   # always harass at any odds
UPGRADE_GOLD_RATIO = 0.40
DIFFICULTY_BONUS   = 600  # gold every 3 turns (more frequent)


def win_prob(my_power: float, enemy_power: float) -> float:
    total = my_power + enemy_power
    return my_power / total if total > 0 else 1.0


class AIController:
    def __init__(self, game_state):
        self.gs = game_state
        self._encircle_target: dict = {}

    def run_enemy_turns(self):
        for clan_name, clan in self.gs.clans.items():
            if clan_name == self.gs.player_clan_name:
                continue
            if not clan.is_alive:
                continue
            self._run_clan_turn(clan)

    def _run_clan_turn(self, clan):
        gs = self.gs

        # 1. Economy
        self._collect_tax(clan)
        self._pay_upkeep(clan)

        # Difficulty scaling — every 3 turns now (was 5)
        if gs.turn > 0 and gs.turn % 3 == 0:
            clan.gold += DIFFICULTY_BONUS * (gs.turn // 3)

        # 2. Tick production queues
        self._tick_ai_queues(clan)

        # 3. Border analysis
        border_provs = self._border_provinces(clan)

        # 4. Upgrade
        self._upgrade_cities(clan, border_provs)

        # 5. Recruit aggressively
        self._recruit_soldiers(clan, border_provs)

        # 6. Consolidate only idle armies at same province (not marching)
        self._consolidate_armies(clan)

        # 7. Pick targets — reassess every turn, no caching
        self._pick_encircle_target(clan)

        # 8. Forest ambush
        self._maybe_hide_in_forest(clan)

        # 9. Every army acts — INCLUDING already-marching armies
        for army in [a for a in gs.armies if a.owner == clan.name and a.is_alive()]:
            self._act(clan, army)

    # ── Economy ───────────────────────────────────────────────────────────────

    def _maybe_hide_in_forest(self, clan):
        forests = getattr(self.gs, 'forests', {})
        if not forests:
            return
        for army in [a for a in self.gs.armies
                     if a.owner == clan.name and a.is_alive()
                     and not a.is_marching() and not getattr(a, 'hidden', False)]:
            for fp in forests.values():
                if fp.can_hide(army) and random.random() < 0.25:
                    fp.enter(army)
                    break

    def _collect_tax(self, clan):
        for prov in list(clan.territories):
            city = self.gs.cities.get(prov)
            if not city:
                continue
            t_min = city.tax_min()
            t_max = city.tax_max()
            t_range = t_max - t_min
            frac = random.uniform(0.72, 0.82) if clan.debt > 0 else random.uniform(0.52, 0.68)
            city.tax_level = int(t_min + t_range * frac)
            clan.collect_tax(city.tax_income())

    def _pay_upkeep(self, clan):
        gs = self.gs
        upkeep = sum(a.maintenance_cost()
                     for a in gs.armies if a.owner == clan.name and a.is_alive())
        clan.gold -= upkeep
        clan.debt = abs(clan.gold) if clan.gold < 0 else 0

    # ── Production ────────────────────────────────────────────────────────────

    def _tick_ai_queues(self, clan):
        gs = self.gs
        for prov in list(clan.territories):
            city = gs.cities.get(prov)
            if not city:
                continue
            ready = city.tick_queues()
            for soldier in ready:
                existing = [a for a in gs.armies
                            if a.owner == clan.name and a.province == prov and a.is_alive()]
                if existing:
                    existing[0].soldiers.append(soldier)
                else:
                    new_army = MapArmy(clan.name, prov, [soldier])
                    new_army.remaining_km = new_army.turn_km_budget()
                    gs.armies.append(new_army)
                gs.log(f"[AI] {clan.name} trained {soldier.name} at {prov}")

    def _upgrade_cities(self, clan, border_provs):
        gs = self.gs
        capital = clan.start_province
        order = (
            [p for p in border_provs if p != capital] +
            ([capital] if capital in clan.territories else []) +
            [p for p in clan.territories if p not in border_provs and p != capital]
        )
        for prov in order:
            city = gs.cities.get(prov)
            if not city or city.city_level >= 5 or city.upgrade_turns_left > 0:
                continue
            cost = CITY_LEVEL_CONFIG[city.city_level]["upgrade_cost"]
            if cost and clan.gold >= cost * UPGRADE_GOLD_RATIO:
                if city.queue_upgrade(clan):
                    gs.log(f"[AI] {clan.name} upgrading {prov}")

    def _recruit_soldiers(self, clan, border_provs):
        gs     = self.gs
        income = sum(gs.cities[p].tax_income()
                     for p in clan.territories if p in gs.cities)
        current_upkeep = sum(a.maintenance_cost()
                             for a in gs.armies if a.owner == clan.name and a.is_alive())
        net = income - current_upkeep

        order = border_provs + [p for p in clan.territories if p not in border_provs]
        for prov in order:
            city = gs.cities.get(prov)
            if not city or not city.can_queue_recruit():
                continue
            cfg           = city._config()
            unit          = clan.default_unit + cfg["soldier_bonus"]
            recruit_cost  = unit * 10
            future_upkeep = unit * 10
            noise         = random.uniform(0.7, 1.3)
            # Recruit much more freely — only block if truly broke
            if clan.gold >= recruit_cost and net * noise - future_upkeep > -income * 0.8:
                if city.queue_recruit(clan):
                    net -= future_upkeep

    # ── Consolidate ───────────────────────────────────────────────────────────

    def _consolidate_armies(self, clan):
        """Only merge idle armies at same province. Leave marching armies alone."""
        gs     = self.gs
        seen   = {}
        remove = []
        for army in [a for a in gs.armies
                     if a.owner == clan.name and a.is_alive() and not a.is_marching()]:
            p = army.province
            if p in seen:
                seen[p].join(army)
                remove.append(army)
            else:
                seen[p] = army
        for a in remove:
            if a in gs.armies:
                gs.armies.remove(a)

    # ── Target selection — reassessed EVERY turn ──────────────────────────────

    def _pick_encircle_target(self, clan):
        """
        Always pick the best target fresh each turn.
        Priority: retake lost > player province > weakest enemy > neutral.
        Neutrals now get NO penalty — grab them.
        """
        gs          = self.gs
        player_name = gs.player_clan_name

        # Retake lost province first
        if clan.retake_target:
            retake_city = gs.cities.get(clan.retake_target)
            if retake_city and retake_city.owner != clan.name:
                self._encircle_target[clan.name] = clan.retake_target
                return
            else:
                clan.retake_target = None

        own_armies = [a for a in gs.armies if a.owner == clan.name and a.is_alive()]
        if not own_armies:
            return

        candidates = []
        for prov, city in gs.cities.items():
            if city.owner == clan.name:
                continue

            # Distance from nearest own army
            dists = []
            for army in own_armies:
                path = bfs_path(army.province, prov,
                                passable_fn=lambda p: self._can_pass(clan, p))
                if path:
                    dists.append(len(path))
            if not dists:
                continue
            dist = min(dists)

            def_power = city.total_defense_power() + sum(
                a.total_power() for a in gs.armies
                if a.province == prov and a.owner != clan.name and a.is_alive())

            # Score: lower = better
            # Strong preference for player (attack them hard)
            # Slight preference for weak enemies over neutrals
            # Neutrals valued — don't penalise them
            player_bonus = -20 if city.owner == player_name else 0
            neutral_val  = -3  if city.owner == "Neutral"   else 0  # slight bonus for free land
            rebel_val    = -5  if city.owner == "Rebels"    else 0  # rebels are easy pickings
            score = dist * 2 + def_power / 600 + player_bonus + neutral_val + rebel_val
            candidates.append((score, prov))

        if candidates:
            self._encircle_target[clan.name] = min(candidates, key=lambda x: x[0])[1]

    # ── Army action ───────────────────────────────────────────────────────────

    def _act(self, clan, army):
        """
        Called for EVERY army every turn, including already-marching ones.
        If a marching army arrives at/adjacent to a target, it acts immediately.
        """
        gs        = self.gs
        neighbors = get_neighbors(army.province)
        my_power  = army.total_power()
        if my_power <= 0:
            return

        # ── 1. Attack adjacent enemy armies ──────────────────────────────────
        adj_enemies = []
        for nb in neighbors:
            for a in gs.armies:
                if a.province == nb and a.owner != clan.name and a.is_alive():
                    adj_enemies.append(a)
        # Also check armies AT this province (may have arrived this turn)
        for a in gs.armies:
            if a.province == army.province and a.owner != clan.name and a.is_alive():
                adj_enemies.append(a)

        # Player armies always first
        adj_enemies.sort(key=lambda a: (0 if a.owner == gs.player_clan_name else 1,
                                         a.total_power()))

        for target in adj_enemies:
            wp = win_prob(my_power, target.total_power())
            if wp >= WIN_PROB_CHIP:
                result = resolve_battle(army, target)
                army.moved_this_turn = True
                army.cancel_march()
                gs.log(f"[AI] {clan.name} {'attacked' if wp >= WIN_PROB_ATTACK else 'pressured'} "
                       f"{target.owner} at {target.province} (wp {wp:.0%})")
                # Log damage taken/dealt for player when AI attacks player
                pcn = gs.player_clan_name
                if target.owner == pcn:
                    evt = "BATTLE_LOSS" if not result.get("defender_wins") else "BATTLE_WIN"
                    gs.stats.log(gs.turn, evt, pcn,
                                 province=target.province,
                                 units=int(result.get("effective_atk_power", 0)),
                                 damage=int(result.get("effective_def_power", 0)),
                                 units_lost=int(result.get("defender_lost", 0)),
                                 provinces=len(gs.player_clan().territories))
                gs.clean_dead_armies()
                gs.check_clan_elimination()
                if not army.is_alive():
                    return
                # After fighting, reassess — break out and fall through to march
                break

        if army.moved_this_turn or not army.is_alive():
            return

        # ── 2. Siege adjacent or current province ────────────────────────────
        siege_candidates = []
        check_provs = list(neighbors) + [army.province]
        for nb in check_provs:
            city = gs.cities.get(nb)
            if not city or city.owner == clan.name:
                continue
            defending_armies = [a for a in gs.armies
                                if a.province == nb and a.owner != clan.name and a.is_alive()]
            total_def = city.total_defense_power() + sum(a.total_power() for a in defending_armies)
            wp = win_prob(my_power, total_def)
            # Prioritise: player > rebels > enemies > neutrals
            prio = (0 if city.owner == gs.player_clan_name else
                    1 if city.owner == "Rebels" else
                    2 if city.owner not in ("Neutral",) else 3)
            siege_candidates.append((prio, -wp, nb, city, defending_armies, total_def, wp))

        siege_candidates.sort(key=lambda x: (x[0], x[1]))

        for prio, neg_wp, target_prov, city, def_armies, total_def, wp in siege_candidates:
            if wp >= WIN_PROB_CHIP:
                old_owner     = city.owner
                old_province  = army.province
                army.province = target_prov
                result = resolve_siege(army, city,
                                       province_key=target_prov,
                                       new_garrison_dmg=clan.default_dmg,
                                       defending_armies=def_armies)
                army.moved_this_turn = True
                # Log when player's province is sieged by AI
                pcn = gs.player_clan_name
                if old_owner == pcn:
                    evt = "SIEGE_LOSS" if result.get("attacker_wins") else "SIEGE_WIN"
                    gs.stats.log(gs.turn, evt, pcn,
                                 province=target_prov,
                                 units=int(result.get("attacker_power", 0)),
                                 damage=int(result.get("defender_power", 0)),
                                 units_lost=int(result.get("defender_lost", 0)),
                                 provinces=len(gs.player_clan().territories))
                if result.get("attacker_wins"):
                    old_clan = gs.clans.get(old_owner)
                    if old_clan and target_prov in old_clan.territories:
                        old_clan.territories.remove(target_prov)
                    if target_prov not in clan.territories:
                        clan.territories.append(target_prov)
                    if self._encircle_target.get(clan.name) == target_prov:
                        self._encircle_target[clan.name] = None
                    army.exhaust(siege=True)
                    gs.log(f"[AI] {clan.name} CONQUERED {target_prov} from {old_owner}! (wp {wp:.0%})")
                    gs.check_clan_elimination()
                else:
                    # Failed siege — snap back position but still counts as moved
                    army.province = old_province
                    gs.log(f"[AI] {clan.name} siege of {target_prov} failed (wp {wp:.0%})")
                gs.clean_dead_armies()
                return

        # ── 3. March toward target ────────────────────────────────────────────
        # Marching armies continue automatically; idle ones pick a destination
        if army.is_marching():
            entered = army.advance_turn()
            army.moved_this_turn = True
            self._process_entered(clan, army, entered)
            return

        # Pick fresh target
        target = self._encircle_target.get(clan.name)
        if not target or gs.cities.get(target, None) and gs.cities[target].owner == clan.name:
            target = self._nearest_enemy_province(clan, army)
            self._encircle_target[clan.name] = target

        if target and target != army.province:
            ok = army.set_march_destination(
                target, passable_fn=lambda p: self._can_pass(clan, p))
            if ok:
                entered = army.advance_turn()
                army.moved_this_turn = True
                gs.log(f"[AI] {clan.name} marching → {target} ({army.turns_to_arrive()}t)")
                self._process_entered(clan, army, entered)
                return

        # ── 4. No target — grab nearest anything ─────────────────────────────
        nearest = self._nearest_enemy_province(clan, army)
        if nearest and nearest != army.province:
            ok = army.set_march_destination(
                nearest, passable_fn=lambda p: self._can_pass(clan, p))
            if ok:
                entered = army.advance_turn()
                army.moved_this_turn = True
                self._process_entered(clan, army, entered)

    def _process_entered(self, clan, army, entered: list):
        """Claim any neutral provinces the army walked through this turn."""
        gs = self.gs
        for prov in entered:
            city = gs.cities.get(prov)
            if city and city.owner == "Neutral":
                city.owner         = clan.name
                city.garrison.owner = clan.name
                if prov not in clan.territories:
                    clan.territories.append(prov)
                army.exhaust(siege=False)
                gs.log(f"[AI] {clan.name} claimed neutral {prov}")
                break
            # Auto-siege if arrived at target
            elif prov == army.siege_target or prov == self._encircle_target.get(clan.name):
                city2 = gs.cities.get(prov)
                if city2 and city2.owner != clan.name and not army.exhausted:
                    def_armies = [a for a in gs.armies
                                  if a.province == prov and a.owner != clan.name and a.is_alive()]
                    total_def  = city2.total_defense_power() + sum(a.total_power() for a in def_armies)
                    wp = win_prob(army.total_power(), total_def)
                    if wp >= WIN_PROB_CHIP:
                        old_owner = city2.owner
                        result = resolve_siege(army, city2, province_key=prov,
                                               new_garrison_dmg=clan.default_dmg,
                                               defending_armies=def_armies)
                        # Log when player's province is sieged by AI (on arrival)
                        pcn = gs.player_clan_name
                        if old_owner == pcn:
                            evt = "SIEGE_LOSS" if result.get("attacker_wins") else "SIEGE_WIN"
                            gs.stats.log(gs.turn, evt, pcn,
                                         province=prov,
                                         units=int(result.get("attacker_power", 0)),
                                         damage=int(result.get("defender_power", 0)),
                                         units_lost=int(result.get("defender_lost", 0)),
                                         provinces=len(gs.player_clan().territories))
                        if result.get("attacker_wins"):
                            old_clan = gs.clans.get(old_owner)
                            if old_clan and prov in old_clan.territories:
                                old_clan.territories.remove(prov)
                            if prov not in clan.territories:
                                clan.territories.append(prov)
                            army.exhaust(siege=True)
                            self._encircle_target[clan.name] = None
                            gs.log(f"[AI] {clan.name} CONQUERED {prov} on arrival! (wp {wp:.0%})")
                            gs.check_clan_elimination()
                        gs.clean_dead_armies()
                        break

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _border_provinces(self, clan) -> list:
        gs = self.gs
        result = []
        for prov in clan.territories:
            for nb in get_neighbors(prov):
                city = gs.cities.get(nb)
                if city and city.owner != clan.name:
                    result.append(prov)
                    break
        return result

    def _nearest_enemy_province(self, clan, army) -> str:
        gs          = self.gs
        player_name = gs.player_clan_name
        best, best_score = None, 9999
        for prov, city in gs.cities.items():
            if city.owner == clan.name:
                continue
            path = bfs_path(army.province, prov,
                            passable_fn=lambda p: self._can_pass(clan, p))
            if not path:
                continue
            dist = len(path)
            prio = (0 if city.owner == player_name else
                    1 if city.owner == "Rebels"    else
                    2 if city.owner != "Neutral"   else 3)
            score = dist + prio * 2
            if score < best_score:
                best_score = score
                best = prov
        return best

    def _can_pass(self, clan, province):
        gs   = self.gs
        city = gs.cities.get(province)
        if city is None:
            return True
        return city.owner in (clan.name, "Neutral", "Rebels")

    def _can_pass_retake(self, clan, province, target):
        return province == target or self._can_pass(clan, province)