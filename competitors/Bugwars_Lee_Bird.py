"""
EEE320 Lab 6: BugWars 2026
Group Members: Lee, Bird
"""
import random
from shared import (
    Creature, Cilia, PhotoGland, Propagator, Cloaking,
    LifeSensor, CreatureTypeSensor, EnergySensor, Spikes,
    Direction, Soil, Plant
)

#TODO: For organs, are we iterating through the priority list every time
#   -If yes, then put a hard cap for photoglands to not waste energy
#   -If no, then why not and do above
#   -TLDR: How are we making organs

#TODO: Stay stable and not move, move through attacking and reproducing
#   -If surrounded by friendlies, no need to make more organs
#   -TLDR: How do we stay stable once we hit the mid/endgame?


class JensenHuang(Creature):
    """
    Main competitor class (declared first per competition rules).
    Cloaked solar predator (3 PhotoGlands = +450/turn + Cloaking + 2 Spikes).
    Appears as empty Soil to enemy sensors while generating +285 net energy/turn,
    ambushing weak enemies and baiting aggressive hunters into losing defensive fights.
    """
    _instance_count = 0

    def __init__(self):
        super().__init__()
        JensenHuang._instance_count += 1
        self.cilia = None
        self.womb = None
        self.cloak_organ = None
        self.life_sensor = None
        self.type_sensor = None
        self.energy_sensor = None
        self.photo_count = 0
        self.spike_count = 0
        self.organs_ready = False

    def do_turn(self):
        # Stage 1 & 2 organ setup
        if not self.organs_ready:
            self.grow_organs()
            return

        # Keep Cloaking active whenever energy is comfortable so enemies see us as Soil
        if self.cloak_organ:
            if self.strength() > 450 and not self.is_cloaked():
                self.cloak_organ.cloak()
            elif self.strength() <= 450 and self.is_cloaked():
                self.cloak_organ.uncloak()

        # Scan neighbors using 1-energy LifeSensor first
        empty_dirs, plant_dirs, prey_dirs = self.scan_surroundings()

        # Replicate aggressively at 1650+ so excess energy compounds into more cloaked hunters
        if self.strength() >= 1650 and self.is_alive():
            self.reproduce(empty_dirs, plant_dirs)

        # Eat plants, snipe profitable enemies, or roam
        if self.is_alive():
            self.forage_and_hunt(empty_dirs, plant_dirs, prey_dirs)

    def is_cloaked(self):
        # Track cloak state safely without calling framework-only f_is_cloaked()
        return getattr(self, '_cloak_active', False)

    def grow_organs(self):
        # Priority 1: 3 PhotoGlands (+450/turn) so energy snowballs immediately
        while self.photo_count < 3 and self.strength() > PhotoGland.CREATION_COST + 10:
            PhotoGland(self)
            self.photo_count += 1

        # Priority 2: Womb (50) + Cilia (100) + LifeSensor (50)
        if not self.womb and self.strength() > Propagator.CREATION_COST + 10:
            self.womb = NvidiaPropagator(self)
        if not self.cilia and self.strength() > Cilia.CREATION_COST + 10:
            self.cilia = Cilia(self)
        if not self.life_sensor and self.strength() > LifeSensor.CREATION_COST + 10:
            self.life_sensor = LifeSensor(self)

        # Priority 3: 2 Spikes (400 defense) + TypeSensor (100) + EnergySensor (100)
        while self.spike_count < 2 and self.strength() > Spikes.CREATION_COST + 10:
            Spikes(self)
            self.spike_count += 1
        if not self.type_sensor and self.strength() > CreatureTypeSensor.CREATION_COST + 10:
            self.type_sensor = CreatureTypeSensor(self)
        if not self.energy_sensor and self.strength() > EnergySensor.CREATION_COST + 10:
            self.energy_sensor = EnergySensor(self)

        # Priority 4: Cloaking (500 cost) once base economy and sensors are online (10/10 slots)
        if not self.cloak_organ and self.strength() > Cloaking.CREATION_COST + 150:
            self.cloak_organ = Cloaking(self)
            self.cloak_organ.cloak()
            self._cloak_active = True

        if (self.photo_count == 3 and self.spike_count == 2 and self.womb
                and self.cilia and self.life_sensor and self.type_sensor
                and self.energy_sensor and self.cloak_organ):
            self.organs_ready = True

    def scan_surroundings(self):
        dirs = list(Direction)
        random.shuffle(dirs)
        empty_dirs = []
        plant_dirs = []
        prey_dirs = []

        for d in dirs:
            if self.strength() < 120:
                break
            # LifeSensor costs 1 energy; returns False for empty Soil (or cloaked enemies)
            if not self.life_sensor.sense(d):
                empty_dirs.append(d)
            else:
                t_type = self.type_sensor.sense(d)
                if t_type == Plant:
                    plant_dirs.append(d)
                elif t_type != JensenHuang and not issubclass(t_type, JensenHuang):
                    enemy_str = self.energy_sensor.sense(d)
                    # Hunt enemies we can beat cleanly even after 400 spike damage
                    if self.strength() > enemy_str + 450:
                        prey_dirs.append((d, enemy_str))

        return empty_dirs, plant_dirs, prey_dirs

    def reproduce(self, empty_dirs, plant_dirs):
        # Give newborn 750 energy so it buys all 3 PhotoGlands on Turn 1
        child_energy = 750
        if self.strength() < child_energy + Propagator.USE_COST + 750:
            return

        if plant_dirs:
            self.womb.give_birth(child_energy, plant_dirs.pop(0))
        elif empty_dirs:
            self.womb.give_birth(child_energy, empty_dirs.pop(0))

    def forage_and_hunt(self, empty_dirs, plant_dirs, prey_dirs):
        if self.strength() < 150:
            return

        # 1. Eat adjacent Plants first
        if plant_dirs:
            self.cilia.move_in_direction(plant_dirs[0])
            return

        # 2. Hunt profitable uncloaked enemies (prefer highest strength we can safely kill)
        if prey_dirs:
            prey_dirs.sort(key=lambda item: item[1], reverse=True)
            self.cilia.move_in_direction(prey_dirs[0][0])
            return

        # 3. Roam into open Soil to find plants and ambush unsuspecting enemies
        if empty_dirs and self.strength() > 300 and random.random() < 0.65:
            self.cilia.move_in_direction(random.choice(empty_dirs))

    @classmethod
    def instance_count(cls):
        return JensenHuang._instance_count

    @classmethod
    def destroyed(cls):
        JensenHuang._instance_count -= 1


class NvidiaPropagator(Propagator):
    def make_child(self):
        return JensenHuang()