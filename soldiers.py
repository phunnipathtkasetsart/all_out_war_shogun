class Troops:
    def __init__(self, name, owner, unit, dmg):
        self.name = name
        self.owner = owner
        self.unit = unit
        self.dmg = dmg

    def power(self):
        return self.unit * self.dmg


class Soldier(Troops):
    def __init__(self, name, owner, unit, dmg):
        super().__init__(name, owner, unit, dmg)
        self.multiplier_power = 1

    def power(self):
        return self.unit * self.dmg * self.multiplier_power

    def take_damage(self, other_power):
        """Calculate units remaining after taking damage from an opposing army."""
        if self.dmg == 0:
            return
        units_lost = other_power / self.dmg
        self.unit = max(0, self.unit - int(units_lost))

    def is_alive(self):
        return self.unit > 0

    def maintenance_cost(self):
        return self.unit * 10

    def __repr__(self):
        return f"Soldier({self.name}, owner={self.owner}, unit={self.unit}, dmg={self.dmg}, multiplier={self.multiplier_power}, power={self.power()})"


class Garrison(Troops):
    def __init__(self, name, owner, unit, dmg):
        super().__init__(name, owner, unit, dmg)

    def power(self):
        return self.unit * self.dmg

    def maintenance_cost(self):
        return self.unit * 10

    def __repr__(self):
        return f"Garrison({self.name}, owner={self.owner}, unit={self.unit}, dmg={self.dmg}, power={self.power()})"
