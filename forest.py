FOREST_POINTS = {
    "Kiso Forest":    {"route": ("Kanto",   "Musashi"),  "frac": 0.50, "pos": (227, 348)},
    "Suruga Woods":   {"route": ("Shimosa",  "Suruga"),  "frac": 0.50, "pos": (590, 341)},
    "Mikawa Thicket": {"route": ("Musashi",  "Totomi"),  "frac": 0.50, "pos": (313, 422)},
    "Owari Grove":    {"route": ("Owari",    "Kyoto"),   "frac": 0.50, "pos": (680, 549)},
    "Mutsu Pines":    {"route": ("Mutsu",    "Dewa"),    "frac": 0.50, "pos": (402, 191)},
}

FOREST_RADIUS = 22   # click hit radius in map coords


class ForestPoint:
    def __init__(self, name: str, route: tuple, frac: float, pos: tuple):
        self.name    = name
        self.route   = route        
        self.frac    = frac         
        self.pos     = pos          
        self.armies: list = []      

    def on_route(self, prov_a: str, prov_b: str) -> bool:
        r = self.route
        return (r[0] == prov_a and r[1] == prov_b) or \
               (r[0] == prov_b and r[1] == prov_a)

    def can_hide(self, army) -> bool:
        if army in self.armies:
            return False  
        if getattr(army, 'hidden', False):
            return False   
        if army.is_marching():
            return False  
        a, b = self.route
        return army.province in (a, b)

    def should_auto_exit(self, army) -> bool:
        if army not in self.armies:
            return False
        a, b = self.route
        if army.is_marching():
            return True
        if army.province not in (a, b):
            return True
        return False

    def enter(self, army):
        """Place army into this forest (hidden)."""
        if army not in self.armies:
            self.armies.append(army)
            army.hidden          = True
            army.forest_point    = self   
            army.forest_pos      = self.pos

    def exit(self, army):
        """Remove army from forest (revealed)."""
        if army in self.armies:
            self.armies.remove(army)
        army.hidden       = False
        army.forest_point = None
        army.forest_pos   = None

    def hidden_armies_of(self, clan_name: str) -> list:
        return [a for a in self.armies if a.owner == clan_name]

    def enemy_armies_of(self, clan_name: str) -> list:
        return [a for a in self.armies if a.owner != clan_name]


# ── Ambush event ──────────────────────────────────────────────────────────────

class AmbushEvent:
    def __init__(self, victim_army, ambushers: list, forest):
        self.victim_army = victim_army
        self.ambushers   = ambushers
        self.forest      = forest
        self.resolved    = False

    def resolve_withdraw(self, game_state):
        army = self.victim_army
        army.march_queue   = []
        army.next_province = None
        army.km_traveled   = 0.0
        army.remaining_km  = 0.0
        army.moved_this_turn = True
        game_state.log(f"⚠ {army.owner} army WITHDREW from ambush at {self.forest.name}!")
        self.resolved = True

    def resolve_fight(self, game_state):
        from combat import resolve_ambush, resolve_battle
        army = self.victim_army
        for ambusher in list(self.ambushers):
            if not ambusher.is_alive() or not army.is_alive():
                break
            result = resolve_ambush(ambusher, army)
            winner = ambusher.owner if result.get("attacker_wins") else army.owner
            game_state.log(
                f"⚔ AMBUSH at {self.forest.name}! "
                f"{ambusher.owner} ambushed {army.owner} "
                f"(first-strike {int(result['ambush_first_strike_power'])}pw) "
                f"→ {winner} wins!"
            )
        for ambusher in list(self.ambushers):
            self.forest.exit(ambusher)
        game_state.clean_dead_armies()
        game_state.check_clan_elimination()
        self.resolved = True


# ── Factory ───────────────────────────────────────────────────────────────────

def make_forest_points() -> dict:
    return {
        name: ForestPoint(name, data["route"], data["frac"], data["pos"])
        for name, data in FOREST_POINTS.items()
    }


def check_ambush(army, game_state) -> "AmbushEvent | None":
    if not army.next_province:
        return None
    forests = getattr(game_state, 'forests', {})
    for fp in forests.values():
        if not fp.on_route(army.province, army.next_province):
            continue
        enemies = fp.enemy_armies_of(army.owner)
        if enemies:
            return AmbushEvent(army, enemies, fp)
    return None