import random
from soldiers import Soldier, Garrison

CITY_NAMES = [
    "Ōtsubashi", "Kushinan", "Kashimanuma", "Yachibetsu", "Okayagi",
    "Tokozen", "Hashikura", "Tamasano", "Hitachiōma", "Higashima",
    "Kushishiki", "Sakuzuka", "Ōmusugi", "Takebashi", "Shiogaya",
    "Kashise", "Minokari", "Yamagatamoto", "Isade", "Minamiagaki",
    "Shiodo", "Chikuwa", "Shioryū", "Yasugōri", "Okatō",
    "Fukutō", "Ōsase", "Yasumizu", "Shimasano", "Ōsagōri",
    "Daide", "Itobe", "Okayakura", "Hitazuka", "Kamogawa",
    "Goseda", "Kamatami", "Urasano", "Yamagachi", "Hitaji",
    "Kawago", "Komatsuki", "Tsukari", "Ōtasano", "Amagano",
    "Ichinosu", "Ishikuni", "Tsurugagōri", "Komashiki", "Fukukuni",
]

# ── City level config ─────────────────────────────────────────────────────────
#
# garrison_unit  : default units in garrison at this level
# soldier_bonus  : extra units added to clan default when recruiting here
# multiplier     : applied to soldier power AND tax income scaling
# tax_min/max    : slider range for this level  (min = 500 * multiplier)
# upgrade_cost   : gold cost to reach the NEXT level (None = max level)
#
CITY_LEVEL_CONFIG = {
    1: {
        "label":        "Village",
        "garrison_unit": 50,
        "soldier_bonus": 10,
        "multiplier":    1,
        "tax_min":       500,
        "tax_max":       1000,
        "upgrade_cost":  1500,
    },
    2: {
        "label":        "Fortress",
        "garrison_unit": 100,
        "soldier_bonus": 30,
        "multiplier":    2,
        "tax_min":       1000,   # 500 * 2
        "tax_max":       2000,   # 1000 * 2
        "upgrade_cost":  3000,
    },
    3: {
        "label":        "Stronghold",
        "garrison_unit": 150,
        "soldier_bonus": 50,
        "multiplier":    3,
        "tax_min":       1500,   # 500 * 3
        "tax_max":       3000,
        "upgrade_cost":  5000,
    },
    4: {
        "label":        "Castle",
        "garrison_unit": 200,
        "soldier_bonus": 80,
        "multiplier":    4,
        "tax_min":       2000,   # 500 * 4
        "tax_max":       4000,
        "upgrade_cost":  8000,
    },
    5: {
        "label":        "Citadel",
        "garrison_unit": 300,
        "soldier_bonus": 100,
        "multiplier":    5,
        "tax_min":       2500,   # 500 * 5
        "tax_max":       5000,
        "upgrade_cost":  None,
    },
}

REBEL_CLAN_NAME = "Rebels"


class City:
    CITY_LEVEL_CONFIG = CITY_LEVEL_CONFIG
    RECRUIT_TURNS  = 2
    UPGRADE_TURNS  = 3
    MAX_QUEUE_SIZE = 3

    def __init__(self, name: str, owner: str, city_level: int = 1,
                 rage_level: int = 3, tax_level: int = None,
                 garrison_dmg: float = 3.0):
        self.name       = name
        self.owner      = owner
        self.city_level = city_level
        self.rage_level = rage_level
        self.garrison_dmg = garrison_dmg        # set from clan dmg at creation
        # Default tax to the minimum for this level
        cfg = CITY_LEVEL_CONFIG[city_level]
        self.tax_level  = tax_level if tax_level is not None else cfg["tax_min"]
        self.stationed_soldiers    = []
        self.garrison              = self._make_garrison()
        self.rage_over_limit_turns    = 0
        self.post_conquest_rage_turns = 0
        self.is_rebel_city: bool      = False
        self.resistance_turns: int    = 0   # "resistance to invaders" penalty turns remaining
        self._rage_pressure_counter: int = 0
        # ── Production queues ─────────────────────────────────────────────────
        self.recruit_queue: list = []   # [(turns_left, Soldier), ...]  max 1 at a time
        self.upgrade_turns_left: int = 0   # 0 = no upgrade in progress

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _config(self):
        return CITY_LEVEL_CONFIG[self.city_level]

    def _make_garrison(self):
        cfg = self._config()
        return Garrison(
            name=f"{cfg['label']} Guard",
            owner=self.owner,
            unit=cfg["garrison_unit"],
            dmg=self.garrison_dmg,          # clan's default dmg, not hardcoded 3
        )

    def tax_min(self):
        return self._config()["tax_min"]

    def tax_max(self):
        return self._config()["tax_max"]

    def multiplier(self):
        return self._config()["multiplier"]

    # ── Tax & Rage ────────────────────────────────────────────────────────────

    def tax_income(self):
        """
        Income = tax_level * city multiplier.
        tax_level is the slider value (min–max for this level).
        multiplier scales both tax and soldier power.
        """
        return self.tax_level * self.multiplier()

    def rage_tax_calc(self, is_player: bool = False):
        """
        Public order system.
        is_player=True  → harder mechanics (passive drift, weak garrison, army matters)
        is_player=False → forgiving AI mechanics (strong suppression, slow rage)
        """
        if is_player:
            return self._rage_tax_calc_player()
        return self._rage_tax_calc_ai()

    def _rage_tax_calc_ai(self):
        """
        Original forgiving rage logic used for AI-owned cities.
        AI always sets max tax, so we keep suppression strong enough
        that they don't constantly rebel.
        """
        t_min   = self.tax_min()
        t_max   = self.tax_max()
        t_range = max(1, t_max - t_min)
        t_mid   = t_min + t_range * 0.5
        t_high  = t_min + t_range * 0.75

        # ── Step 1: tax pressure ──────────────────────────────────────────────
        if self.tax_level > t_high:
            self._rage_pressure_counter += 1
            if self._rage_pressure_counter >= 2:
                self.rage_level = min(6, self.rage_level + 1)
                self._rage_pressure_counter = 0
        elif self.tax_level > t_mid:
            self._rage_pressure_counter += 1
            if self._rage_pressure_counter >= 5:
                self.rage_level = min(6, self.rage_level + 1)
                self._rage_pressure_counter = 0
        else:
            self._rage_pressure_counter = 0

        # ── Step 2: resistance to invaders penalty ────────────────────────────
        if self.resistance_turns > 0:
            self.rage_level = min(6, self.rage_level + 1)
            self.resistance_turns -= 1

        # ── Step 3: military suppression (strong — AI garrison holds order) ───
        military_units = self.garrison.unit
        for s in self.stationed_soldiers:
            military_units += s.unit
        suppression = military_units / 10

        if self.post_conquest_rage_turns > 0:
            if suppression > self.rage_level + 1:
                self.rage_level = max(1, self.rage_level - 1)
            self.post_conquest_rage_turns -= 1
        else:
            if suppression > self.rage_level:
                self.rage_level = max(1, self.rage_level - 1)

        # ── Step 4: rebellion tracking ────────────────────────────────────────
        if self.rage_level > 5:
            self.rage_over_limit_turns += 1
        else:
            self.rage_over_limit_turns = 0

        if self.rage_over_limit_turns > 3:
            return "rebellion"
        elif self.rage_over_limit_turns > 0:
            turns_left = max(1, 4 - self.rage_over_limit_turns)
            return f"warning_{turns_left}"
        return None

    def _rage_tax_calc_player(self):
        """Harder rage logic for player-owned cities."""
        t_min   = self.tax_min()
        t_max   = self.tax_max()
        t_range = max(1, t_max - t_min)
        t_mid   = t_min + t_range * 0.5
        t_high  = t_min + t_range * 0.75

        # ── Step 1: passive unrest drift ─────────────────────────────────────
        # Every city has some baseline unrest — populations are never perfectly
        # content. Higher city level = more complex society = faster drift.
        # Village: +1 every 6t  Fortress: every 5t  Stronghold: every 4t
        # Castle: every 3t      Citadel: every 2t
        drift_interval = max(2, 7 - self.city_level)   # 6,5,4,3,2
        self._rage_pressure_counter += 1
        if self._rage_pressure_counter >= drift_interval:
            self.rage_level = min(6, self.rage_level + 1)
            self._rage_pressure_counter = 0

        # ── Step 2: tax pressure on top of drift ─────────────────────────────
        # Low tax slows / cancels drift. High tax adds extra rage immediately.
        if self.tax_level > t_high:
            # Max tax bracket: extra +1 rage every turn (stacks with drift)
            self.rage_level = min(6, self.rage_level + 1)
        elif self.tax_level <= t_min:
            # Minimum tax: reward — cancel this turn's drift tick if it fired
            # (rage was already incremented above; undo it)
            self.rage_level = max(1, self.rage_level - 1)
        # Mid-low tax (t_min < tax <= t_mid): no extra pressure, drift only
        # Mid-high tax (t_mid < tax <= t_high): drift only (already faster at high levels)

        # ── Step 3: resistance to invaders ───────────────────────────────────
        if self.resistance_turns > 0:
            # Conquered city: flat +1 rage per turn regardless of tax
            self.rage_level = min(3, self.rage_level + 1)
            self.resistance_turns -= 1

        # ── Step 4: military suppression ─────────────────────────────────────
        # Garrison is a small standing guard — provides minimal suppression.
        # A stationed army (player armies at this province) meaningfully
        # pacifies the population through visible military presence.
        # High city levels are harder to suppress — drift is faster, cap lower.
        #
        # Garrison:  unit / 80   → Castle 200u = 2.5  (weak — it's just guards)
        # Army:      unit / 20   → 600u = 30.0         (strong — visible force)
        # Garrison capped at 3.0 regardless of size (it's a garrison, not army)
        # Army capped at (8 - city_level): Village=7, Castle=4, Citadel=3
        garrison_sup = min(self.garrison.unit / 80, 3.0)
        army_sup     = sum(s.unit for s in self.stationed_soldiers) / 20
        army_cap     = max(1, 8 - self.city_level)   # 7,6,5,4,3
        army_sup     = min(army_sup, army_cap)
        suppression  = garrison_sup + army_sup

        # Suppression > rage → rage decreases by 1.
        # Post-conquest window: need suppression > rage+1 (active resistance).
        if self.post_conquest_rage_turns > 0:
            threshold = self.rage_level + 1
            self.post_conquest_rage_turns -= 1
        else:
            threshold = self.rage_level

        if suppression > threshold:
            self.rage_level = max(1, self.rage_level - 1)

        # ── Step 5: rebellion tracking + warning ──────────────────────────────
        if self.rage_level > 5:
            self.rage_over_limit_turns += 1
        else:
            self.rage_over_limit_turns = 0

        if self.rage_over_limit_turns > 3:
            return "rebellion"
        elif self.rage_over_limit_turns > 0:
            turns_left = max(1, 4 - self.rage_over_limit_turns)
            return f"warning_{turns_left}"
        return None

    # ── Recruit ───────────────────────────────────────────────────────────────

    def recruit_cost(self, unit_amount: int) -> int:
        return unit_amount * 10

    def can_queue_recruit(self) -> bool:
        """True if there is room to queue another recruit order."""
        return (len(self.recruit_queue) < self.MAX_QUEUE_SIZE
                and self.upgrade_turns_left == 0)

    def queue_recruit(self, clan) -> bool:
        """
        Pay gold upfront and add a soldier to the recruit queue (2 turns).
        Returns True on success, False if can't afford or queue full.
        """
        if not self.can_queue_recruit():
            return False
        cfg  = self._config()
        base_unit = clan.default_unit + cfg["soldier_bonus"]
        # Apply clan recruit bonus (Nori gets +30% troops)
        unit = int(base_unit * getattr(clan, 'recruit_bonus', 1.0))
        cost = self.recruit_cost(unit)
        if not clan.can_afford(cost):
            return False
        clan.gold -= cost
        soldier = Soldier(
            name=clan.default_name,
            owner=clan.name,
            unit=unit,
            dmg=clan.default_dmg,
        )
        soldier.multiplier_power = cfg["multiplier"]
        self.recruit_queue.append([self.RECRUIT_TURNS, soldier])
        return True

    def tick_queues(self) -> list:
        """
        Advance all production queues by 1 turn.
        Returns list of completed Soldier objects ready to spawn.
        """
        ready = []
        still_building = []
        for entry in self.recruit_queue:
            entry[0] -= 1
            if entry[0] <= 0:
                ready.append(entry[1])
            else:
                still_building.append(entry)
        self.recruit_queue = still_building

        if self.upgrade_turns_left > 0:
            self.upgrade_turns_left -= 1
            if self.upgrade_turns_left == 0:
                # Upgrade fires now
                self.city_level += 1
                cfg = self._config()
                self.tax_level = max(self.tax_level, cfg["tax_min"])
                self.garrison  = self._make_garrison()

        return ready

    # ── Upgrade ───────────────────────────────────────────────────────────────

    def can_queue_upgrade(self) -> bool:
        return (self.city_level < 5
                and self.upgrade_turns_left == 0
                and len(self.recruit_queue) == 0)

    def queue_upgrade(self, clan) -> bool:
        """
        Pay gold upfront, start a 3-turn upgrade countdown.
        Returns True on success.
        """
        if not self.can_queue_upgrade():
            return False
        cost = self._config()["upgrade_cost"]
        if not cost or not clan.can_afford(cost):
            return False
        clan.gold -= cost
        self.upgrade_turns_left = self.UPGRADE_TURNS
        return True

    # ── Conquest ─────────────────────────────────────────────────────────────

    def on_conquered(self, new_owner: str, new_garrison_dmg: float = None):
        """
        Called when city is captured by a new clan.

        RESISTANCE TO INVADERS:
          Sets resistance_turns based on city level — bigger, more developed
          cities have populations more entrenched with the old ruler.
          Village=3, Fortress=4, Stronghold=5, Castle=6, Citadel=8 turns

        Rage inherits old owner's rage + 1 (capped at 6).
        Post-conquest suppression window = 3 turns (stricter military needed).
        Rebel city reconquest gets longer window (5 turns).
        """
        # Resistance to invaders: scales with city development
        resistance_by_level = {1: 3, 2: 4, 3: 5, 4: 6, 5: 8}
        self.resistance_turns = resistance_by_level.get(self.city_level, 3)
        if getattr(self, 'is_rebel_city', False):
            self.resistance_turns += 1   # rebel cities resist even harder

        inherited_rage = min(6, self.rage_level + 1)

        self.owner = new_owner
        if new_garrison_dmg is not None:
            self.garrison_dmg = new_garrison_dmg
        self.garrison = self._make_garrison()
        self.stationed_soldiers = []
        self.rage_level = inherited_rage
        self.post_conquest_rage_turns = 5 if getattr(self, 'is_rebel_city', False) else 3
        self.is_rebel_city = False
        self._rage_pressure_counter = 0

    def on_rebelled(self):
        """
        City rebels — becomes independent Rebels faction.
        Marks is_rebel_city so reconquering owner knows rage will be elevated.
        """
        old_owner = self.owner
        self.owner = REBEL_CLAN_NAME
        self.garrison_dmg = 3.0
        self.garrison = self._make_garrison()
        self.stationed_soldiers = []
        self.rage_over_limit_turns = 0
        self.rage_level = 5
        self.is_rebel_city = True   # flag — rage stays +1 for 5 turns after reconquest
        return old_owner

    # ── Defense power ─────────────────────────────────────────────────────────

    def total_defense_power(self):
        power = self.garrison.power()
        for s in self.stationed_soldiers:
            power += s.power()
        return power

    def label(self):
        return CITY_LEVEL_CONFIG[self.city_level]["label"]

    def __repr__(self):
        return (f"City({self.name}, owner={self.owner}, level={self.label()}, "
                f"rage={self.rage_level}, tax={self.tax_level})")


# ── Convenience factory ───────────────────────────────────────────────────────

def make_city(name: str, owner: str, level: int = 1,
              garrison_dmg: float = 3.0) -> City:
    return City(name=name, owner=owner, city_level=level,
                garrison_dmg=garrison_dmg)