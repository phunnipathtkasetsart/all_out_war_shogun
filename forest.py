"""
forest.py  –  Forest ambush points on the map.

Forests are independent objects sitting ON routes between provinces.
Any army marching through a route with a forest passes through it.
An army can ORDER to hide in a forest — it becomes invisible to enemies.
When an enemy army marches INTO a route that has a hidden army, an
AMBUSH EVENT fires: the marching player gets a quick-event popup:
  [Withdraw] – cancel march, army retreats to origin province
  [Fight]    – battle resolves immediately (ambusher gets first-strike bonus)
"""

# ── Forest definitions ────────────────────────────────────────────────────────
# Each forest sits ON a route at a fractional position (0.0 = origin, 1.0 = dest).
# frac=0.5 means exactly midway. Two armies can use the same forest.

FOREST_POINTS = {
    "Kiso Forest":    {"route": ("Kanto",   "Musashi"),  "frac": 0.50, "pos": (227, 348)},
    "Suruga Woods":   {"route": ("Shimosa",  "Suruga"),  "frac": 0.50, "pos": (590, 341)},
    "Mikawa Thicket": {"route": ("Musashi",  "Totomi"),  "frac": 0.50, "pos": (313, 422)},
    "Owari Grove":    {"route": ("Owari",    "Kyoto"),   "frac": 0.50, "pos": (680, 549)},
    "Mutsu Pines":    {"route": ("Mutsu",    "Dewa"),    "frac": 0.50, "pos": (402, 191)},
}

FOREST_RADIUS = 22   # click hit radius in map coords


class ForestPoint:
    """
    A forest ambush location sitting on a route.
    Armies stationed here are hidden from enemies.
    """
    def __init__(self, name: str, route: tuple, frac: float, pos: tuple):
        self.name    = name
        self.route   = route        # (province_a, province_b)  — undirected
        self.frac    = frac         # position along route  0.0–1.0
        self.pos     = pos          # pixel position (pre-computed midpoint)
        self.armies: list = []      # MapArmy objects currently hiding here

    def on_route(self, prov_a: str, prov_b: str) -> bool:
        """True if this forest sits on the route between prov_a and prov_b."""
        r = self.route
        return (r[0] == prov_a and r[1] == prov_b) or \
               (r[0] == prov_b and r[1] == prov_a)

    def can_hide(self, army) -> bool:
        """Army can enter forest if at a route endpoint and not already here."""
        if army in self.armies:
            return False   # already here
        if getattr(army, 'hidden', False):
            return False   # already hiding somewhere else
        if army.is_marching():
            return False   # can't enter forest while mid-march
        a, b = self.route
        return army.province in (a, b)

    def should_auto_exit(self, army) -> bool:
        """
        Returns True if army should automatically leave this forest.
        Triggers when the army starts marching or moves to a province
        that is no longer an endpoint of this forest's route.
        """
        if army not in self.armies:
            return False
        a, b = self.route
        # Auto-exit if army started marching away
        if army.is_marching():
            return True
        # Auto-exit if army has moved to a different province
        if army.province not in (a, b):
            return True
        return False

    def enter(self, army):
        """Place army into this forest (hidden)."""
        if army not in self.armies:
            self.armies.append(army)
            army.hidden          = True
            army.forest_point    = self   # back-reference
            # Snap army position to forest for rendering
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
    """
    Fired when a marching army enters a route that contains hidden enemy armies.
    The event is shown to the relevant player (human or AI).

    victim_army   : the army that was ambushed (marching)
    ambushers     : list of enemy MapArmy objects hiding in the forest
    forest        : the ForestPoint where this occurred
    """
    def __init__(self, victim_army, ambushers: list, forest):
        self.victim_army = victim_army
        self.ambushers   = ambushers
        self.forest      = forest
        self.resolved    = False

    def resolve_withdraw(self, game_state):
        """Victim withdraws — army retreats to origin province, loses remaining km."""
        army = self.victim_army
        # Snap back to departure province (province field before next_province)
        army.march_queue   = []
        army.next_province = None
        army.km_traveled   = 0.0
        army.remaining_km  = 0.0
        army.moved_this_turn = True
        game_state.log(f"⚠ {army.owner} army WITHDREW from ambush at {self.forest.name}!")
        self.resolved = True

    def resolve_fight(self, game_state):
        """Victim fights back — ambushers get first-strike, then normal battle."""
        from combat import resolve_ambush, resolve_battle
        army = self.victim_army
        # All ambushers attack together
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
        # Ambushers are revealed after fighting
        for ambusher in list(self.ambushers):
            self.forest.exit(ambusher)
        game_state.clean_dead_armies()
        game_state.check_clan_elimination()
        self.resolved = True


# ── Factory ───────────────────────────────────────────────────────────────────

def make_forest_points() -> dict:
    """Return a fresh dict of all ForestPoint instances."""
    return {
        name: ForestPoint(name, data["route"], data["frac"], data["pos"])
        for name, data in FOREST_POINTS.items()
    }


def check_ambush(army, game_state) -> "AmbushEvent | None":
    """
    Call when an army moves onto a route segment.
    Returns an AmbushEvent if hidden enemy armies are on that route, else None.
    """
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