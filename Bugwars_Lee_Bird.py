"""
EEE320 Lab 6: BugWars 2026
Group Members: Lee, Bird
"""
import random
from shared import (
    Creature, Cilia, PhotoGland, Propagator,
    CreatureTypeSensor, EnergySensor, PoisonSensor, Spikes,
    Direction, Soil, Plant
)


class JensenHuang(Creature):
    """
    Main competitor class:
    Mobile solar hunter-gatherer with staged organ growth, offensive birthing,
    and caste specialization into stationary SolarBastions in dense territory.
    """
    _instance_count = 0  # Shared population counter for both JensenHuang and SolarBastion

    def __init__(self):
        super().__init__()
        JensenHuang._instance_count += 1  # Track new instance on birth
        self.cilia = None
        self.womb = None
        self.type_sensor = None
        self.energy_sensor = None
        self.poison_sensor = None
        self.photo_count = 0
        self.spike_count = 0
        self.organs_ready = False

    def do_turn(self):
        # Prioritize growing all 10 organs before moving or reproducing
        if not self.organs_ready:
            self.grow_organs()
            return

        # Spend excess energy before f_cap_strength() trims strength back down to 2000
        if self.strength() >= 1750:
            self.reproduce()

        # Look for nearby plants to eat, weak enemies to attack, or empty soil to explore
        if self.is_alive():
            self.forage_or_hunt()

    def grow_organs(self):
        # Stage 1: Grow 2 PhotoGlands (+300/turn) and 3 Spikes (600 defense) first for early survival
        while self.photo_count < 2 and self.strength() > PhotoGland.CREATION_COST + 150:
            PhotoGland(self)
            self.photo_count += 1
        while self.spike_count < 3 and self.strength() > Spikes.CREATION_COST + 150:
            Spikes(self)
            self.spike_count += 1

        # Wait until Stage 1 finishes and we have at least 750 reserve strength for Stage 2
        if self.photo_count < 2 or self.spike_count < 3 or self.strength() < 750:
            return

        # Stage 2: Build mobility, sensors, and womb (uses remaining 5 slots -> 10/10 total)
        if not self.womb and self.strength() > Propagator.CREATION_COST + 150:
            self.womb = NvidiaPropagator(self)
        if not self.cilia and self.strength() > Cilia.CREATION_COST + 150:
            self.cilia = Cilia(self)
        if not self.type_sensor and self.strength() > CreatureTypeSensor.CREATION_COST + 150:
            self.type_sensor = CreatureTypeSensor(self)
        if not self.energy_sensor and self.strength() > EnergySensor.CREATION_COST + 150:
            self.energy_sensor = EnergySensor(self)
        if not self.poison_sensor and self.strength() > PoisonSensor.CREATION_COST + 150:
            self.poison_sensor = PoisonSensor(self)

        # Flip flag once all 10 organs are installed
        if (self.photo_count == 2 and self.spike_count == 3 and self.womb
                and self.cilia and self.type_sensor and self.energy_sensor
                and self.poison_sensor):
            self.organs_ready = True

    def reproduce(self):
        dirs = list(Direction)
        random.shuffle(dirs)  # Randomize scan direction to avoid directional bias
        ally_neighbors = 0
        target_dir = None

        for d in dirs:
            if self.strength() < 1200:
                return  # Abort if sensor pings drain too much strength
            t_type = self.type_sensor.sense(d)

            # Count adjacent allies (both JensenHuang and SolarBastion) to gauge crowding
            if t_type == JensenHuang or issubclass(t_type, JensenHuang):
                ally_neighbors += 1
                continue

            if target_dir is None:
                if t_type == Soil or t_type == Plant:
                    target_dir = d  # Safe empty or plant square for a newborn
                elif not self.poison_sensor.sense(d):
                    # Offensive birthing: drop a newborn onto a weak enemy for an instant attack
                    enemy_str = self.energy_sensor.sense(d)
                    child_preview = (self.strength() - Propagator.USE_COST) / 2
                    if child_preview > enemy_str + 250:
                        target_dir = d

        if target_dir is not None:
            # Spawn a stationary SolarBastion if crowded (3+ allies), otherwise a mobile bug
            self.womb.spawn_bastion = (ally_neighbors >= 3 and random.random() < 0.5)
            child_energy = (self.strength() - Propagator.USE_COST) / 2
            if child_energy > 450:
                self.womb.give_birth(child_energy, target_dir)

    def forage_or_hunt(self):
        dirs = list(Direction)
        random.shuffle(dirs)
        empty_dirs = []
        best_prey_dir = None
        lowest_enemy_str = 9999

        for d in dirs:
            if self.strength() < 120:
                return  # Hold position and let PhotoGlands recharge strength
            t_type = self.type_sensor.sense(d)

            # Skip friendly units
            if t_type == JensenHuang or issubclass(t_type, JensenHuang):
                continue

            if t_type == Soil:
                empty_dirs.append(d)
            elif t_type == Plant:
                self.cilia.move_in_direction(d)  # Eat plant immediately (plants don't fight back)
                return
            else:
                # Target the weakest non-poisonous enemy with a 250-strength safety buffer
                if not self.poison_sensor.sense(d):
                    enemy_str = self.energy_sensor.sense(d)
                    if self.strength() > enemy_str + 250 and enemy_str < lowest_enemy_str:
                        lowest_enemy_str = enemy_str
                        best_prey_dir = d

        # Attack weakest safe prey if found, otherwise roam into empty soil 45% of the time
        if best_prey_dir is not None:
            self.cilia.move_in_direction(best_prey_dir)
        elif empty_dirs and self.strength() > 350 and random.random() < 0.45:
            self.cilia.move_in_direction(random.choice(empty_dirs))

    @classmethod
    def instance_count(cls):
        return JensenHuang._instance_count

    @classmethod
    def destroyed(cls):
        JensenHuang._instance_count -= 1  # Explicitly decrement JensenHuang counter per rules


class SolarBastion(JensenHuang):
    """
    Stationary helper subclass. Must inherit from JensenHuang and must NOT
    override _instance_count, instance_count(), or destroyed().
    Builds 1 Propagator, 1 CreatureTypeSensor, 5 PhotoGlands (+750/turn), and 3 Spikes (600 defense).
    """
    def __init__(self):
        super().__init__()  # Calls JensenHuang.__init__() to increment shared _instance_count

    def do_turn(self):
        # Grow stationary solar generator and defensive spikes
        if not self.organs_ready:
            if not self.womb and self.strength() > Propagator.CREATION_COST + 100:
                self.womb = NvidiaPropagator(self)
            if not self.type_sensor and self.strength() > CreatureTypeSensor.CREATION_COST + 100:
                self.type_sensor = CreatureTypeSensor(self)
            while self.spike_count < 3 and self.strength() > Spikes.CREATION_COST + 100:
                Spikes(self)
                self.spike_count += 1
            while self.photo_count < 5 and self.strength() > PhotoGland.CREATION_COST + 100:
                PhotoGland(self)
                self.photo_count += 1

            # Mark setup complete once all 10 organs are installed
            if (self.womb and self.type_sensor
                    and self.spike_count == 3 and self.photo_count == 5):
                self.organs_ready = True
            return

        # Pump out mobile JensenHuang bugs into non-allied squares whenever energy overflows
        if self.strength() >= 1500:
            dirs = list(Direction)
            random.shuffle(dirs)
            for d in dirs:
                if self.strength() < 900:
                    break
                t_type = self.type_sensor.sense(d)
                # Check for non-allies so newborns don't attack adjacent friendly bugs
                if t_type != JensenHuang and not issubclass(t_type, JensenHuang):
                    self.womb.spawn_bastion = False
                    self.womb.give_birth(700, d)
                    break


class NvidiaPropagator(Propagator):
    def __init__(self, host):
        super().__init__(host)
        self.spawn_bastion = False  # Toggled by parent bug to choose between mobile and bastion offspring

    def make_child(self):
        if self.spawn_bastion:
            return SolarBastion()
        return JensenHuang()