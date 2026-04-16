from soldiers import Soldier
from ui import RED, BLUE, GREEN, GOLD_COLOR

# ── Clan matchup damage multipliers ──────────────────────────────────────────
# clan_dmg_bonus[attacker][defender] = extra multiplier on top of base damage
CLAN_MATCHUP = {
    "Tada": {"Date": 1.30},   # Tada cavalry crushes Date swordsmen
    "Date": {"Nori": 1.30},   # Date odachi shreds Nori ashigaru
    "Abe":  {"Tada": 1.35},   # Abe yari specialist counters Tada cavalry
    "Nori": {},                # Nori has no specific matchup bonus
}

def get_matchup_mult(attacker: str, defender: str) -> float:
    """Return damage multiplier for attacker vs defender (default 1.0)."""
    return CLAN_MATCHUP.get(attacker, {}).get(defender, 1.0)


class Clan:
    def __init__(self, name: str, gold: int, territories: list, soldiers: list,
                 default_name: str, default_unit: int, default_dmg: float,
                 color: tuple, start_province: str,
                 recruit_bonus: float = 1.0):
        self.name = name
        self.gold = gold
        self.territories = territories
        self.soldiers    = soldiers
        self.default_name = default_name
        self.default_unit = default_unit
        self.default_dmg  = default_dmg
        self.color        = color
        self.start_province = start_province
        self.recruit_bonus  = recruit_bonus   # multiplier on recruited unit count
        self.is_alive = True
        self.debt     = 0
        self.retake_target = None

    def total_power(self):
        return sum(s.power() for s in self.soldiers)

    def total_maintenance(self):
        return sum(s.maintenance_cost() for s in self.soldiers)

    def collect_tax(self, amount):
        self.gold += amount

    def deduct_maintenance(self):
        cost = self.total_maintenance()
        self.gold -= cost
        if self.gold < 0:
            self.debt = abs(self.gold)
        else:
            self.debt = 0

    def can_afford(self, amount):
        return self.gold >= amount

    def spawn_default_soldier(self, unit_bonus=0, multiplier=1):
        s = Soldier(self.default_name, self.name,
                    int((self.default_unit + unit_bonus) * self.recruit_bonus),
                    self.default_dmg)
        s.multiplier_power = multiplier
        return s

    def __repr__(self):
        return f"Clan({self.name}, gold={self.gold}, territories={self.territories})"


def make_clans():
    """Return a fresh dict of all clan instances."""
    return {
        "Tada": Clan(
            name="Tada",
            gold=1500, #debug 150000000
            territories=["Kyoto"],
            soldiers=[],
            default_name="Katana Cavalry",
            default_unit=55, #debug 55000
            default_dmg=10.5,           # slightly higher — elite cavalry
            color=RED,
            start_province="Kyoto",
            recruit_bonus=1.0,
        ),
        "Date": Clan(
            name="Date",
            gold=1500,
            territories=["Mutsu"],
            soldiers=[],
            default_name="Odachi Senshi",
            default_unit=60, 
            default_dmg=10.0,           # highest base dmg — odachi specialists
            color=BLUE,
            start_province="Mutsu",
            recruit_bonus=1.0,
        ),
        "Nori": Clan(
            name="Nori",
            gold=1500,
            territories=["Osaka"],
            soldiers=[],
            default_name="Katana Ashigaru",
            default_unit=180,
            default_dmg=2.9,
            color=(80, 180, 80),
            start_province="Osaka",
            recruit_bonus=1.30,         # Nori recruits 30% more troops per order
        ),
        "Abe": Clan(
            name="Abe",
            gold=1500,
            territories=["Edo"],
            soldiers=[],
            default_name="Yari Senshi",
            default_unit=100,
            default_dmg=6.2,            # higher base dmg — yari formation is deadly
            color=(180, 80, 220),
            start_province="Edo",
            recruit_bonus=1.0,
        ),
    }