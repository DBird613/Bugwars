"""
EEE320 Lab 6: BugWars 2026
Group Members: Lee, Bird
"""
import random
from shared import (
    Creature, Cilia, PhotoGland, Propagator, Cloaking, PoisonGland,
    CreatureTypeSensor, EnergySensor, PoisonSensor, Spikes,
    Direction, Soil, Plant
)


class JensenHuang(Creature):
    """
    Main competitor class (declared first per competition rules).
    Combines high-speed solar replication (3 PhotoGlands, 2 Spikes) with
    CloakedAmbusher stealth assassins and PoisonSensor safety checks.
    """
    _instance_count = 0

    def __init__(self):
        super().__init__()
        JensenHuang._instance_count += 1
        self.cilia = None
        self.womb = None
        self.type_sensor = None
        self.energy_sensor = None
        self.poison_sensor = None
        self.photo_count = 0
        self.spike_count = 0
        self.organs_ready = False

    def do_turn(self):
        if not self.organs_ready:
            self.grow_organs()
            return

        if self.strength() >= 1500:
            self.reproduce()

        if self.is_alive():
            self.act()

    def grow_organs(self):
        # Stage 1: 3 PhotoGlands (+450/turn) and 2 Spikes (400 defense)
        while self.photo_count < 3 and self.strength() > PhotoGland.CREATION_COST + 100:
            PhotoGland(self)
            self.photo_count += 1
        while self.spike_count < 2 and self.strength() > Spikes.CREATION_COST + 100:
            Spikes(self)
            self.spike_count += 1

        if self.photo_count < 3 or self.spike_count < 2 or self.strength() < 500:
            return

        # Stage 2: Movement, propagator, and sensors (10/10 slots total)
        if not self.womb and self.strength() > Propagator.CREATION_COST + 100:
            self.womb = NvidiaPropagator(self)
        if not self.cilia and self.strength() > Cilia.CREATION_COST + 100:
            self.cilia = Cilia(self)
        if not self.type_sensor and self.strength() > CreatureTypeSensor.CREATION_COST + 100:
            self.type_sensor = CreatureTypeSensor(self)
        if not self.energy_sensor and self.strength() > EnergySensor.CREATION_COST + 100:
            self.energy_sensor = EnergySensor(self)
        if not self.poison_sensor and self.strength() > PoisonSensor.CREATION_COST + 100:
            self.poison_sensor = PoisonSensor(self)

        if (self.photo_count == 3 and self.spike_count == 2 and self.womb
                and self.cilia and self.type_sensor and self.energy_sensor
                and self.poison_sensor):
            self.organs_ready = True

    def reproduce(self):
        dirs = list(Direction)
        random.shuffle(dirs)
        for d in dirs:
            if self.strength() < 1100:
                return
            t_type = self.type_sensor.sense(d)
            if (t_type == Soil or t_type == Plant) and not self.poison_sensor.sense(d):
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

            if t_type == JensenHuang or issubclass(t_type, JensenHuang):
                continue

            if t_type == Soil:
                if not self.poison_sensor.sense(d):
                    empty_dirs.append(d)
            elif t_type == Plant:
                self.cilia.move_in_direction(d)
                return
            else:
                if not self.poison_sensor.sense(d):
                    enemy_str = self.energy_sensor.sense(d)
                    if self.strength() > enemy_str + 50:
                        self.cilia.move_in_direction(d)
                        return

        if empty_dirs and self.strength() > 250 and random.random() < 0.6:
            self.cilia.move_in_direction(random.choice(empty_dirs))

    @classmethod
    def instance_count(cls):
        return JensenHuang._instance_count

    @classmethod
    def destroyed(cls):
        JensenHuang._instance_count -= 1


class CloakedAmbusher(JensenHuang):
    """
    Stealth assassin subclass. Shares JensenHuang._instance_count.
    Appears as empty Soil (strength 0) to enemy sensors, rushes nearby targets,
    and carries a PoisonGland to punish attackers.
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
            if not self.poison_sensor and self.strength() > PoisonSensor.CREATION_COST + 50:
                self.poison_sensor = PoisonSensor(self)
            if not self.poison_gland and self.strength() > PoisonGland.CREATION_COST + 50:
                self.poison_gland = PoisonGland(self)
                self.poison_gland.add_poison(100)

            if (self.cloak_organ and self.cilia and self.type_sensor
                    and self.poison_sensor):
                self.organs_ready = True
            return

        if self.strength() < 250 and self.cloak_organ:
            self.cloak_organ.uncloak()

        dirs = list(Direction)
        random.shuffle(dirs)
        safe_dirs = []
        for d in dirs:
            if self.strength() < 50:
                return
            t_type = self.type_sensor.sense(d)
            if t_type == JensenHuang or issubclass(t_type, JensenHuang):
                continue
            if not self.poison_sensor.sense(d):
                if t_type != Soil:
                    self.cilia.move_in_direction(d)
                    return
                safe_dirs.append(d)

        if safe_dirs and self.strength() > 150:
            self.cilia.move_in_direction(random.choice(safe_dirs))


class NvidiaPropagator(Propagator):
    def __init__(self, host):
        super().__init__(host)
        self.spawn_ambusher = False

    def make_child(self):
        if self.spawn_ambusher:
            return CloakedAmbusher()
        return JensenHuang()
