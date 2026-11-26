"""
EEE320 Lab 6: BugWars 2026
Sparring Partner Competitor for Local Testing
"""
import random
from shared import (
    Creature, Cilia, PhotoGland, Propagator, Cloaking, PoisonGland,
    CreatureTypeSensor, EnergySensor, Spikes,
    Direction, Soil, Plant
)


class RivalBug(Creature):
    """
    Main sparring competitor (declared first per competition rules).
    Combines aggressive solar replication with CloakedAmbushers and PoisonGlands
    to stress-test JensenHuang's sensors and defensive spikes.
    """
    _instance_count = 0

    def __init__(self):
        super().__init__()
        RivalBug._instance_count += 1
        self.cilia = None
        self.womb = None
        self.type_sensor = None
        self.energy_sensor = None
        self.photo_count = 0
        self.spike_count = 0
        self.organs_ready = False

    def do_turn(self):
        if not self.organs_ready:
            self.grow_organs()
            return

        # Rapidly replicate when strength builds up
        if self.strength() >= 1500:
            self.reproduce()

        if self.is_alive():
            self.act()

    def grow_organs(self):
        # Build 3 PhotoGlands (+450/turn) and 2 Spikes (400 defense) first
        while self.photo_count < 3 and self.strength() > PhotoGland.CREATION_COST + 100:
            PhotoGland(self)
            self.photo_count += 1
        while self.spike_count < 2 and self.strength() > Spikes.CREATION_COST + 100:
            Spikes(self)
            self.spike_count += 1

        if self.photo_count < 3 or self.spike_count < 2 or self.strength() < 500:
            return

        # Add movement, propagator, and basic sensors (9/10 slots)
        if not self.womb and self.strength() > Propagator.CREATION_COST + 100:
            self.womb = RivalPropagator(self)
        if not self.cilia and self.strength() > Cilia.CREATION_COST + 100:
            self.cilia = Cilia(self)
        if not self.type_sensor and self.strength() > CreatureTypeSensor.CREATION_COST + 100:
            self.type_sensor = CreatureTypeSensor(self)
        if not self.energy_sensor and self.strength() > EnergySensor.CREATION_COST + 100:
            self.energy_sensor = EnergySensor(self)

        if (self.photo_count == 3 and self.spike_count == 2 and self.womb
                and self.cilia and self.type_sensor and self.energy_sensor):
            self.organs_ready = True

    def reproduce(self):
        dirs = list(Direction)
        random.shuffle(dirs)
        for d in dirs:
            if self.strength() < 1100:
                return
            t_type = self.type_sensor.sense(d)
            if t_type == Soil or t_type == Plant:
                # 35% chance to spawn a CloakedAmbusher to bypass enemy sensors
                self.womb.spawn_ambusher = (random.random() < 0.35)
                child_energy = 750 if self.womb.spawn_ambusher else 550
                if self.strength() > child_energy + Propagator.USE_COST + 100:
                    self.womb.give_birth(child_energy, d)
                break

    def act(self):
        dirs = list(Direction)
        random.shuffle(dirs)
        empty_dirs = []

        for d in dirs:
            if self.strength() < 100:
                return
            t_type = self.type_sensor.sense(d)

            # Skip allies
            if t_type == RivalBug or issubclass(t_type, RivalBug):
                continue

            if t_type == Soil:
                empty_dirs.append(d)
            elif t_type == Plant:
                self.cilia.move_in_direction(d)
                return
            else:
                # Aggressive attack without checking poison (tests your spikes/defense)
                enemy_str = self.energy_sensor.sense(d)
                if self.strength() > enemy_str + 50:
                    self.cilia.move_in_direction(d)
                    return

        if empty_dirs and self.strength() > 250 and random.random() < 0.6:
            self.cilia.move_in_direction(random.choice(empty_dirs))

    @classmethod
    def instance_count(cls):
        return RivalBug._instance_count

    @classmethod
    def destroyed(cls):
        RivalBug._instance_count -= 1


class CloakedAmbusher(RivalBug):
    """
    Stealth assassin subclass. Appears as Soil (strength 0) to enemy sensors,
    rushes nearby targets, and carries a PoisonGland to punish attackers.
    """
    def __init__(self):
        super().__init__()
        self.cloak_organ = None
        self.poison_gland = None

    def do_turn(self):
        if not self.organs_ready:
            if not self.cloak_organ and self.strength() > Cloaking.CREATION_COST + 100:
                self.cloak_organ = Cloaking(self)
                self.cloak_organ.cloak()
            if not self.cilia and self.strength() > Cilia.CREATION_COST + 100:
                self.cilia = Cilia(self)
            if not self.type_sensor and self.strength() > CreatureTypeSensor.CREATION_COST + 100:
                self.type_sensor = CreatureTypeSensor(self)
            if not self.poison_gland and self.strength() > PoisonGland.CREATION_COST + 50:
                self.poison_gland = PoisonGland(self)
                self.poison_gland.add_poison(100)  # 400 defensive poison damage

            if self.cloak_organ and self.cilia and self.type_sensor:
                self.organs_ready = True
            return

        # Uncloak if energy gets low so upkeep doesn't kill it
        if self.strength() < 250 and self.cloak_organ:
            self.cloak_organ.uncloak()

        # Ambush any non-ally adjacent square
        dirs = list(Direction)
        random.shuffle(dirs)
        for d in dirs:
            if self.strength() < 50:
                return
            t_type = self.type_sensor.sense(d)
            if t_type != Soil and t_type != RivalBug and not issubclass(t_type, RivalBug):
                self.cilia.move_in_direction(d)
                return

        # Roam rapidly across the map
        if self.strength() > 150:
            self.cilia.move_in_direction(Direction.random())


class RivalPropagator(Propagator):
    def __init__(self, host):
        super().__init__(host)
        self.spawn_ambusher = False

    def make_child(self):
        if self.spawn_ambusher:
            return CloakedAmbusher()
        return RivalBug()