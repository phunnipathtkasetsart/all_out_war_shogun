import math
from collections import deque

# ── Province screen positions (960×720 map canvas) ──────────────────────────
PROVINCE_POSITIONS = {
    "Mutsu":   (519, 170),
    "Dewa":   (285, 213),
    "Sendai":   (680, 226),
    "Kanto":   (285, 308),
    "Shimosa":   (590, 305),
    "Musashi":   (170, 388),
    "Suruga":   (590, 378),
    "Edo":   (170, 470),
    "Totomi":   (456, 457),
    "Mikawa":   (456, 534),
    "Owari":   (644, 518),
    "Kyoto":   (716, 581),
    "Omi":   (860, 530),
    "Osaka":   (788, 637),
    "Shikoku":   (627, 645),
    "Kyushu":   (492, 645),
}

# ── Routes ───────────────────────────────────────────────────────────────────
ROUTES = [
    ("Mutsu",   "Dewa"),
    ("Mutsu",   "Sendai"),
    ("Dewa",    "Kanto"),
    ("Sendai",  "Shimosa"),
    ("Kanto",   "Shimosa"),
    ("Kanto",   "Musashi"),
    ("Shimosa", "Suruga"),
    ("Musashi", "Edo"),
    ("Suruga",  "Totomi"),
    ("Musashi", "Totomi"),
    ("Edo",     "Totomi"),
    ("Totomi",  "Mikawa"),
    ("Mikawa",  "Owari"),
    ("Owari",   "Kyoto"),
    ("Owari",   "Omi"),
    ("Omi",     "Kyoto"),
    ("Kyoto",   "Osaka"),
    ("Osaka",   "Shikoku"),
    ("Shikoku", "Kyushu"),
]

# ── Terrain ──────────────────────────────────────────────────────────────────
TERRAIN = {
    "Mutsu":   "plain",
    "Dewa":    "mountain",
    "Sendai":  "forest",
    "Kanto":   "plain",
    "Shimosa": "plain",
    "Musashi": "forest",
    "Suruga":  "mountain",
    "Edo":     "plain",
    "Totomi":  "forest",
    "Mikawa":  "plain",
    "Owari":   "plain",
    "Kyoto":   "plain",
    "Omi":     "mountain",
    "Osaka":   "plain",
    "Shikoku": "forest",
    "Kyushu":  "plain",
}

CLAN_STARTS = {
    "Tada": "Kyoto",
    "Date": "Mutsu",
    "Nori": "Osaka",
    "Abe":  "Edo",
}

TERRAIN_COLORS = {
    "plain":    (180, 210, 140),
    "forest":   (60,  140,  60),
    "mountain": (140, 120,  90),
}

NODE_RADIUS   = 38
PIXEL_TO_KM   = 0.25   # scale factor: pixels → km

# ── Route distances (km) ─────────────────────────────────────────────────────
def _calc_route_km():
    km = {}
    for a, b in ROUTES:
        pa, pb = PROVINCE_POSITIONS[a], PROVINCE_POSITIONS[b]
        px = math.hypot(pb[0]-pa[0], pb[1]-pa[1])
        dist = round(px * PIXEL_TO_KM, 1)
        km[(a, b)] = dist
        km[(b, a)] = dist
    return km

ROUTE_KM: dict = _calc_route_km()

def route_km(a: str, b: str) -> float:
    """Return km distance between two adjacent provinces."""
    return ROUTE_KM.get((a, b), 30.0)

# ── Speed model ───────────────────────────────────────────────────────────────
SPEED_SMALL  = 30.0   
SPEED_MEDIUM = 25.0   
SPEED_LARGE  = 10.0   
MOUNTAIN_MULT = 0.65  

# Clan-specific speed multipliers
CLAN_SPEED_MULT = {
    "Tada": 1.35,   
    "Nori": 1.25,   
    "Date": 1.0,    
    "Abe":  0.80,   
}

def army_speed(power: float, terrain: str, owner: str = "") -> float:
    if power >= 5000:
        base = SPEED_LARGE
    elif power >= 1500:
        base = SPEED_MEDIUM
    else:
        base = SPEED_SMALL
    if terrain == "mountain":
        base *= MOUNTAIN_MULT
    base *= CLAN_SPEED_MULT.get(owner, 1.0)
    return base

# ── Graph helpers ─────────────────────────────────────────────────────────────
def build_adjacency():
    adj = {p: [] for p in PROVINCE_POSITIONS}
    for a, b in ROUTES:
        adj[a].append(b)
        adj[b].append(a)
    return adj

ADJACENCY = build_adjacency()

def get_neighbors(province: str) -> list:
    return ADJACENCY.get(province, [])

def are_adjacent(a: str, b: str) -> bool:
    return b in ADJACENCY.get(a, [])

def bfs_path(start: str, goal: str, passable_fn=None) -> list:
    if start == goal:
        return [start]
    visited = {start}
    queue   = deque([[start]])
    while queue:
        path    = queue.popleft()
        current = path[-1]
        for nb in ADJACENCY.get(current, []):
            if nb in visited:
                continue
            if passable_fn and not passable_fn(nb):
                continue
            new_path = path + [nb]
            if nb == goal:
                return new_path
            visited.add(nb)
            queue.append(new_path)
    return []

# ── MapArmy ───────────────────────────────────────────────────────────────────
class MapArmy:
    def __init__(self, owner: str, province: str, soldiers: list):
        self.owner          = owner
        self.province       = province
        self.soldiers       = soldiers
        self.march_queue    : list  = []
        self.next_province  : str | None = None
        self.km_traveled    : float = 0.0   
        self.remaining_km   : float = 0.0   
        self.moved_this_turn: bool  = False
        self.has_marched    : bool  = False
        self.is_ambushing   : bool  = False
        self.exhausted      : bool  = False  
        self.siege_exhausted_turns: int = 0  
        self.siege_target   : str | None = None  
        self.hidden         : bool  = False  

    # ── Stats ─────────────────────────────────────────────────────────────────

    def total_power(self) -> float:
        return sum(s.power() for s in self.soldiers)

    def total_units(self) -> int:
        return sum(s.unit for s in self.soldiers)

    def is_alive(self) -> bool:
        return any(s.is_alive() for s in self.soldiers)

    def maintenance_cost(self) -> int:
        return sum(s.maintenance_cost() for s in self.soldiers)

    def can_ambush(self) -> bool:
        return TERRAIN.get(self.province) == "forest"

    def can_hide(self) -> bool:
        """Army can hide only when stationed in forest terrain."""
        return TERRAIN.get(self.province) == "forest"

    def is_visible_to(self, viewer_clan: str) -> bool:
        """
        Returns True if this army is visible to the given clan.
        Hidden armies are invisible to all except their own clan.
        """
        if self.owner == viewer_clan:
            return True
        return not self.hidden

    def speed_this_turn(self) -> float:
        terrain = TERRAIN.get(self.next_province or self.province, "plain")
        return army_speed(self.total_power(), terrain)

    def turn_km_budget(self) -> float:
        """Total km this army can travel in one full turn (clan speed bonus applied)."""
        return army_speed(self.total_power(),
                          TERRAIN.get(self.province, "plain"),
                          self.owner)

    # ── March queue setup ─────────────────────────────────────────────────────

    def set_march_destination(self, destination: str, passable_fn=None) -> bool:
        path = bfs_path(self.province, destination, passable_fn)
        if len(path) < 2:
            return False
        self.march_queue   = path[1:]
        self.next_province = self.march_queue[0]
        self.km_traveled   = 0.0
        return True

    def cancel_march(self):
        self.march_queue   = []
        self.next_province = None
        self.km_traveled   = 0.0
        self.siege_target  = None

    def is_marching(self) -> bool:
        return bool(self.march_queue) or self.next_province is not None

    def reset_turn(self):
        self.moved_this_turn = False
        self.has_marched     = False
        self.is_ambushing    = False
        # Automatically un-hide if army is no longer in forest
        if self.hidden and TERRAIN.get(self.province) != "forest":
            self.hidden = False
        # Siege exhaustion lasts 2 turns — count down each reset
        if self.siege_exhausted_turns > 0:
            self.siege_exhausted_turns -= 1
            self.exhausted = self.siege_exhausted_turns > 0
        else:
            self.exhausted = False
        self.remaining_km = self.turn_km_budget() if not self.exhausted else 0.0
        # siege_target persists across turns — cleared only on arrival or cancel

    def turns_to_arrive(self) -> int:
        """Rough estimate of turns remaining (ignores partial progress)."""
        if not self.march_queue and not self.next_province:
            return 0
        total_km = (route_km(self.province, self.next_province) - self.km_traveled
                    if self.next_province else 0)
        for i in range(len(self.march_queue) - 1 if self.next_province else len(self.march_queue)):
            idx = i if self.next_province else i
            if idx + 1 < len(self.march_queue):
                total_km += route_km(self.march_queue[idx], self.march_queue[idx+1])
        spd = self.turn_km_budget()
        return max(1, math.ceil(total_km / spd)) if spd > 0 else 99

    # ── Per-turn advance (called by game_state.end_turn) ─────────────────────
    def advance_turn(self) -> list:
        if self.exhausted or not self.next_province:
            return []
        if self.remaining_km <= 0:
            self.remaining_km = self.turn_km_budget()
        
        budget = self.remaining_km
        entered = []

        while budget > 0 and self.next_province:
            seg_km    = route_km(self.province, self.next_province)
            remaining = seg_km - self.km_traveled
            
            if budget >= remaining:
                budget          -= remaining
                self.km_traveled = 0.0
                self.province    = self.next_province
                entered.append(self.province)
                self.has_marched = True

                if self.march_queue:
                    self.march_queue.pop(0)
                if self.march_queue:
                    self.next_province = self.march_queue[0]
                else:
                    self.next_province = None
                    break
            else:
                self.km_traveled += budget
                budget            = 0
                self.has_marched  = True

        self.remaining_km    = budget
        self.moved_this_turn = True
        return entered

    def exhaust(self, siege: bool = False):
        """
        Call after conquering/claiming a province.
        siege=True: army cannot march for 2 full turns (siege recovery).
        siege=False: normal conquest — blocked only this turn (e.g. neutral claim).
        """
        self.exhausted       = True
        self.remaining_km    = 0.0
        self.march_queue     = []
        self.next_province   = None
        self.km_traveled     = 0.0
        self.moved_this_turn = True
        self.siege_exhausted_turns = 2 if siege else 1

    # ── Screen position for rendering ─────────────────────────────────────────

    def screen_pos(self) -> tuple:
        """
        Returns (x, y) pixel position for rendering.
        If mid-route, interpolates between province nodes.
        """
        if not self.next_province or self.km_traveled <= 0:
            return PROVINCE_POSITIONS.get(self.province, (0, 0))

        seg_km = route_km(self.province, self.next_province)
        frac   = min(1.0, self.km_traveled / seg_km) if seg_km > 0 else 0.0

        p1 = PROVINCE_POSITIONS[self.province]
        p2 = PROVINCE_POSITIONS[self.next_province]
        x  = int(p1[0] + (p2[0] - p1[0]) * frac)
        y  = int(p1[1] + (p2[1] - p1[1]) * frac)
        return (x, y)

    # ── Legacy compatibility helpers (used by game.py / ai.py) ───────────────

    def do_step(self, destination: str):
        """Single-step helper (used by AI for immediate 1-province moves)."""
        self.province       = destination
        self.km_traveled    = 0.0
        self.moved_this_turn = True
        self.has_marched    = True

    def reachable_next_steps(self, passable_fn=None) -> list:
        """Returns adjacent provinces reachable with remaining km budget."""
        result = []
        budget = self.remaining_km if self.remaining_km > 0 else self.turn_km_budget()
        for nb in ADJACENCY.get(self.province, []):
            if passable_fn and not passable_fn(nb):
                continue
            if route_km(self.province, nb) <= budget:
                result.append(nb)
        return result

    def adjacent_enemy_armies(self, all_armies: list, owner: str) -> list:
        neighbors = ADJACENCY.get(self.province, [])
        return [a for a in all_armies
                if a.owner != owner and a.is_alive()
                and (a.province in neighbors or a.next_province in neighbors)]

    def adjacent_enemy_provinces(self, cities: dict, owner: str) -> list:
        neighbors = ADJACENCY.get(self.province, [])
        return [nb for nb in neighbors
                if cities.get(nb) and cities[nb].owner != owner
                and cities[nb].owner != "Neutral"]

    def join(self, other_army):
        self.soldiers.extend(other_army.soldiers)
        other_army.soldiers = []

    # Legacy — still referenced in some places
    def total_move_points(self) -> int:
        spd = self.turn_km_budget()
        return max(1, int(spd // 25))

    def step_cost(self, destination: str) -> int:
        return 2 if TERRAIN.get(destination) == "mountain" else 1

    def __repr__(self):
        pos = f"mid-route→{self.next_province}@{self.km_traveled:.1f}km" if self.next_province else self.province
        return (f"MapArmy({self.owner}@{pos}, "
                f"power={self.total_power():.0f}, units={self.total_units()})")