"""
combat.py  –  Resolves all combat: Attack, Siege, Ambush.

Power model
───────────
  Group total power  = sum(s.unit * s.dmg * s.multiplier) for all soldiers
  Avg dmg of group   = total_power / total_units  (weighted average damage per unit)
  Units lost (side)  = enemy_total_power / avg_dmg_of_this_side
                     = enemy_total_power * total_units / total_power

This guarantees:
  5 soldiers × power 100 each = 500 total  →  same loss as  1 soldier × power 500
Losses are then spread proportionally across all soldier objects on that side.
"""

# Lazy import to avoid circular dependency (clans imports ui imports map)
def _get_matchup_mult(attacker: str, defender: str) -> float:
    try:
        from clans import get_matchup_mult
        return get_matchup_mult(attacker, defender)
    except Exception:
        return 1.0


# ── Group helpers ─────────────────────────────────────────────────────────────

def group_power(soldiers: list) -> float:
    """Sum of all soldier/garrison power in a group."""
    return sum(s.power() for s in soldiers)


def group_units(soldiers: list) -> int:
    """Total unit count across all soldiers in a group."""
    return sum(s.unit for s in soldiers)


def units_lost(enemy_power: float, my_soldiers: list) -> int:
    """
    How many total units this side loses when hit by enemy_power.
    Uses weighted-average dmg so that 10 weak objects = 1 strong object
    at equal total power.

    Formula:  units_lost = enemy_power * total_units / total_power
    (Derived from:  units_lost = enemy_power / avg_dmg
                    avg_dmg    = total_power / total_units)

    Floors at 1 so every battle always costs something.
    """
    my_power = group_power(my_soldiers)
    my_units = group_units(my_soldiers)
    if my_power <= 0 or my_units <= 0:
        return my_units          # wipe out if somehow power is 0
    lost = (enemy_power * my_units) / my_power
    return max(1, int(lost))


def apply_losses(soldiers: list, total_lost: int):
    """
    Spread `total_lost` units across soldier objects proportionally to their
    current unit count, then remove dead ones.
    Returns the survivors list.
    """
    total = group_units(soldiers)
    remaining_to_lose = total_lost

    for s in soldiers:
        if remaining_to_lose <= 0:
            break
        # Proportional share of losses for this object
        share = int(total_lost * s.unit / total) if total > 0 else remaining_to_lose
        share = min(share, s.unit, remaining_to_lose)
        s.unit -= share
        remaining_to_lose -= share

    # If rounding left some losses unassigned, take from the first survivor
    for s in soldiers:
        if remaining_to_lose <= 0:
            break
        take = min(remaining_to_lose, s.unit)
        s.unit -= take
        remaining_to_lose -= take

    return [s for s in soldiers if s.unit > 0]


# ── Battle ────────────────────────────────────────────────────────────────────

def resolve_battle(attacker_army, defender_army):
    """
    Field battle between two MapArmy objects.
    Both sides take losses simultaneously based on group totals.
    """
    atk_soldiers = attacker_army.soldiers
    def_soldiers = defender_army.soldiers

    atk_power = group_power(atk_soldiers)
    def_power = group_power(def_soldiers)

    # Clan matchup bonus: e.g. Tada hits Date harder
    atk_mult = _get_matchup_mult(attacker_army.owner, defender_army.owner)
    def_mult = _get_matchup_mult(defender_army.owner, attacker_army.owner)
    effective_atk = atk_power * atk_mult
    effective_def = def_power * def_mult

    atk_units_before = attacker_army.total_units()
    def_units_before = defender_army.total_units()

    atk_lost = units_lost(effective_def, atk_soldiers)
    def_lost = units_lost(effective_atk, def_soldiers)

    attacker_army.soldiers = apply_losses(atk_soldiers, atk_lost)
    defender_army.soldiers = apply_losses(def_soldiers, def_lost)

    atk_alive = attacker_army.is_alive()
    def_alive  = defender_army.is_alive()

    return {
        "attacker_power":          atk_power,
        "defender_power":          def_power,
        "effective_atk_power":     effective_atk,   # actual dmg dealt to defender
        "effective_def_power":     effective_def,   # actual dmg dealt to attacker
        "attacker_lost":           atk_lost,
        "defender_lost":           def_lost,
        "attacker_wins":           atk_alive and not def_alive,
        "defender_wins":           def_alive and not atk_alive,
        "draw":                    not atk_alive and not def_alive,
        "attacker_units_left":     attacker_army.total_units(),
        "defender_units_left":     defender_army.total_units(),
        "attacker_units_before":   atk_units_before,
        "defender_units_before":   def_units_before,
    }


# ── Siege ─────────────────────────────────────────────────────────────────────

def resolve_siege(attacker_army, city, province_key: str = None,
                  new_garrison_dmg: float = None, defending_armies: list = None):
    """
    Siege a City.

    Defenders = garrison + city.stationed_soldiers + any MapArmy objects
                physically present at the province (defending_armies).

    All defender soldiers are pooled into one group for power calculation.
    province_key: map node name so attacker moves to correct province on win.
    defending_armies: list of MapArmy objects at the province (passed from caller).
    """
    if defending_armies is None:
        defending_armies = []

    # Pool ALL defender soldiers: garrison + stationed + armies at province
    def_soldiers = [city.garrison] + list(city.stationed_soldiers)
    for da in defending_armies:
        def_soldiers.extend(da.soldiers)

    atk_soldiers = attacker_army.soldiers

    atk_power = group_power(atk_soldiers)
    def_power = group_power(def_soldiers)

    atk_lost = units_lost(def_power, atk_soldiers)
    def_lost = units_lost(atk_power, def_soldiers)

    survivors_atk = apply_losses(atk_soldiers, atk_lost)
    survivors_def = apply_losses(def_soldiers, def_lost)

    attacker_army.soldiers = survivors_atk

    # Re-distribute survivors back: garrison first, then stationed, then armies
    def_idx = 0
    # Garrison
    if def_idx < len(survivors_def):
        city.garrison = survivors_def[def_idx]; def_idx += 1
    else:
        city.garrison.unit = 0
    # Stationed soldiers
    new_stationed = []
    for s in city.stationed_soldiers:
        if def_idx < len(survivors_def):
            new_stationed.append(survivors_def[def_idx]); def_idx += 1
    city.stationed_soldiers = new_stationed
    # Defending armies — put remaining survivors back into first defending army
    remaining = survivors_def[def_idx:]
    if defending_armies:
        defending_armies[0].soldiers = remaining
        for da in defending_armies[1:]:
            da.soldiers = []
    # Remove dead defending armies (caller must clean up)

    garrison_alive  = city.garrison.unit > 0
    stationed_alive = any(s.unit > 0 for s in city.stationed_soldiers)
    armies_alive    = any(da.soldiers for da in defending_armies)
    defender_alive  = garrison_alive or stationed_alive or armies_alive
    attacker_wins   = attacker_army.is_alive() and not defender_alive

    result = {
        "attacker_power":      atk_power,
        "defender_power":      def_power,
        "attacker_lost":       atk_lost,
        "defender_lost":       def_lost,
        "attacker_wins":       attacker_wins,
        "attacker_units_left": attacker_army.total_units(),
        "city":                city.name,
        "defending_armies":    defending_armies,
    }

    if attacker_wins:
        city.on_conquered(attacker_army.owner, new_garrison_dmg=new_garrison_dmg)
        if province_key:
            attacker_army.province = province_key
        result["new_owner"] = attacker_army.owner

    return result


# ── Ambush ────────────────────────────────────────────────────────────────────

def resolve_ambush(ambusher_army, victim_army):
    """
    Ambush: ambusher's group power is doubled for a first strike.
    Victim takes full first-strike damage before they can fight back.
    Only valid from forest terrain (enforced in game.py).
    """
    atk_soldiers = ambusher_army.soldiers
    def_soldiers = victim_army.soldiers

    # First strike: attacker power × 2
    normal_atk_power     = group_power(atk_soldiers)
    first_strike_power   = normal_atk_power * 2

    def_lost_first = units_lost(first_strike_power, def_soldiers)
    victim_army.soldiers = apply_losses(def_soldiers, def_lost_first)

    result = {"ambush_first_strike_power": first_strike_power,
              "first_strike_def_lost":     def_lost_first}

    if victim_army.is_alive():
        # Victim fights back normally
        battle = resolve_battle(ambusher_army, victim_army)
        result.update(battle)
    else:
        result.update({
            "attacker_wins":       True,
            "defender_wins":       False,
            "draw":                False,
            "attacker_units_left": ambusher_army.total_units(),
            "defender_units_left": 0,
        })

    return result