"""
EEE320 Lab 6: BugWars 2026
Lethal Toxic Predator for Local Testing (2,000-Damage PoisonGland + Heavy Mines)
"""
import random
from shared import (
    Creature, Cilia, PhotoGland, Propagator, PoisonGland,
    CreatureTypeSensor, PoisonSensor,
    Direction, Soil, Plant
)


class ToxicViper(Creature):
    """
    Main sparring competitor (declared first per competition rules).
    Arms a 500-volume PoisonGland (4 * 500 = 2,000 defensive damage, lethal to any
    non-poison-checking attacker), replicates rapidly, and seeds heavy PoisonDrops.
    """
    _instance_count = 0

    def __init__(self):
        super().__init__()
        ToxicViper._instance_count += 1
        self.cilia = None
        self.womb = None
        self.poison_gland = None
        self.type_sensor = None
        self.poison_sensor = None
        self.photo_count = 0
        self.organs_ready = False

    def do_turn(self):
        if not self.organs_ready:
            self.grow_organs()
            return

        # Keep poison reservoir charged to 500 (deals 4 * 500 = 2,000 lethal damage on death)
        if self.poison_gland and self.poison_gland.current_volume() < 500 and self.strength() > 250:
            needed = min(500 - self.poison_gland.current_volume(), self.strength() - 150)
            if needed > 0:
                self.poison_gland.add_poison(needed)

        # Replicate aggressively once poison reservoir is charged and strength hits 1500+
        if self.strength() >= 1500 and self.poison_gland.current_volume() >= 350 and self.is_alive():
            self.reproduce()

        # Harvest plants, lay lethal 300-volume mines, or expand
        if self.is_alive():
            self.act()

    def grow_organs(self):
        # Priority 1: 2 PhotoGlands (+300/turn) + PoisonGland (500 cost) so it arms immediately
        while self.photo_count < 2 and self.strength() > PhotoGland.CREATION_COST + 10:
            PhotoGland(self)
            self.photo_count += 1

        if not self.poison_gland and self.strength() > PoisonGland.CREATION_COST + 10:
            self.poison_gland = PoisonGland(self)
            # Immediately load starter poison so Turn-1 rushers die if they attack us
            if self.strength() > 200:
                self.poison_gland.add_poison(min(250, self.strength() - 100))

        # Priority 2: Womb (50) + Cilia (100) + TypeSensor (100) + PoisonSensor (50) = 8/10 slots
        if not self.womb and self.strength() > Propagator.CREATION_COST + 10:
            self.womb = ViperPropagator(self)
        if not self.cilia and self.strength() > Cilia.CREATION_COST + 10:
            self.cilia = Cilia(self)
        if not self.type_sensor and self.strength() > CreatureTypeSensor.CREATION_COST + 10:
            self.type_sensor = CreatureTypeSensor(self)
        if not self.poison_sensor and self.strength() > PoisonSensor.CREATION_COST + 10:
            self.poison_sensor = PoisonSensor(self)

        if (self.photo_count == 2 and self.poison_gland and self.womb
                and self.cilia and self.type_sensor and self.poison_sensor):
            self.organs_ready = True

    def reproduce(self):
        dirs = list(Direction)
        random.shuffle(dirs)
        for d in dirs:
            if self.strength() < 1200:
                return
            t_type = self.type_sensor.sense(d)
            # Birth onto Plants first for an instant meal, or clean Soil
            if (t_type == Plant or t_type == Soil) and not self.poison_sensor.sense(d):
                self.womb.give_birth(800, d)
                return

    def act(self):
        dirs = list(Direction)
        random.shuffle(dirs)
        safe_empty_dirs = []

        for d in dirs:
            if self.strength() < 100:
                return
            t_type = self.type_sensor.sense(d)

            # Skip allies
            if t_type == ToxicViper or issubclass(t_type, ToxicViper):
                continue

            if t_type == Plant:
                self.cilia.move_in_direction(d)
                return
            elif t_type == Soil:
                # Never step on our own PoisonDrop mines
                if not self.poison_sensor.sense(d):
                    safe_empty_dirs.append(d)

        # Drop a heavy 300-volume PoisonDrop mine (1,200 damage!) when reservoir is full
        if safe_empty_dirs and self.poison_gland.current_volume() >= 450 and self.strength() > 500 and random.random() < 0.45:
            mine_dir = safe_empty_dirs.pop(0)
            self.poison_gland.drop_poison(mine_dir, 300)

        # Roam into clean Soil to spread mines and harvest plants
        if safe_empty_dirs and self.strength() > 200 and random.random() < 0.65:
            self.cilia.move_in_direction(random.choice(safe_empty_dirs))

    @classmethod
    def instance_count(cls):
        return ToxicViper._instance_count

    @classmethod
    def destroyed(cls):
        ToxicViper._instance_count -= 1


class ViperPropagator(Propagator):
    def make_child(self):
        return ToxicViper()