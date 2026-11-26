"""
Zeus: A dual-caste artillery fortress and mobile paratrooper competitor
designed as a high-tier benchmark opponent for BugBattle.
"""

import random
from shared import (
    Creature,
    Propagator,
    PhotoGland,
    Cilia,
    CreatureTypeSensor,
    EnergySensor,
    PoisonSensor,
    PoisonGland,
    Direction,
    Soil,
    Plant,
)

ALL_DIRS = tuple(Direction)
POISON_CAPACITY = 1000


class Zeus(Creature):
    """
    Main fortress caste (10 organs total, built PhotoGlands-first):
      - 5 PhotoGlands (+750 energy/turn, always processed first in metabolic cycle)
      - 1 Propagator
      - 1 CreatureTypeSensor
      - 1 PoisonGland
      - 1 PoisonSensor
      - 1 EnergySensor
      Net: +680 energy/turn once fully built.
    """

    __instance_count = 0

    def __init__(self):
        super().__init__()
        Zeus.__instance_count += 1
        self.womb = None
        self.type_sensor = None
        self.energy_sensor = None
        self.poison_sensor = None
        self.poison = None
        self.photo_count = 0
        self.next_child_type = "zeus"
        self.last_enemy_dirs = []
        self.last_non_ally_dirs = []
        self.expected_babies = set()

    @classmethod
    def instance_count(cls):
        return Zeus.__instance_count

    @classmethod
    def destroyed(cls):
        Zeus.__instance_count -= 1

    def do_turn(self):
        # Dead man's switch: if fatally poisoned earlier this turn, strength is <= 0
        # but drop_poison costs 0 energy, so dump remaining poison on threat tiles.
        if self.strength() <= 0:
            self._martyr_strike()
            return

        # ALWAYS build all 5 PhotoGlands first so f_metabolic_cycle() adds +750
        # before subtracting any organ maintenance costs.
        while self.photo_count < 5 and self.strength() > PhotoGland.CREATION_COST + 5:
            PhotoGland(self)
            self.photo_count += 1

        if self.photo_count < 5:
            return

        # Core organs right after PhotoGlands are complete
        if not self.womb and self.strength() > Propagator.CREATION_COST + 5:
            self.womb = ZeusPropagator(self)

        if not self.type_sensor and self.strength() > CreatureTypeSensor.CREATION_COST + 5:
            self.type_sensor = CreatureTypeSensor(self)

        if not self.type_sensor or self.strength() <= 30:
            return

        enemies, plants, safe_soil, ally_count, cloaked_suspects = self._scan_neighbors()

        # Priority 1: Active enemy defense and artillery strikes
        if enemies:
            if not self.poison and self.strength() > PoisonGland.CREATION_COST + 5:
                self.poison = PoisonGland(self)
            if self.poison:
                enemies.sort(key=lambda item: item[1], reverse=True)
                for d, e_str in enemies:
                    self._snipe_enemy(d, e_str, min_keep_strength=150)

        # Priority 2: Cloak-buster strike if a baby vanished onto an empty-looking tile
        if cloaked_suspects and self.poison and self.strength() > 1500:
            for d in cloaked_suspects:
                self._snipe_enemy(d, 2200, min_keep_strength=1100)

        # Priority 3: Finish remaining support organs (10 organs total)
        self._grow_support_organs()

        # Priority 4: Load PoisonGland armor (up to 4000 defensive damage)
        if self.poison:
            if ally_count == 8:
                # Interior fortress tile: stay topped off and return fast for high TPS
                self._top_up_poison(POISON_CAPACITY, min_keep_strength=1900)
                return
            keep_floor = 900 if enemies else 1300
            self._top_up_poison(POISON_CAPACITY, min_keep_strength=keep_floor)

        # Priority 5: Expand and harvest Plants
        if self.womb:
            self._expand(plants, safe_soil, bool(enemies))

    def _grow_support_organs(self):
        if not self.poison and self.strength() > PoisonGland.CREATION_COST + 5:
            self.poison = PoisonGland(self)

        if not self.poison_sensor and self.strength() > PoisonSensor.CREATION_COST + 5:
            self.poison_sensor = PoisonSensor(self)

        if not self.energy_sensor and self.strength() > EnergySensor.CREATION_COST + 5:
            self.energy_sensor = EnergySensor(self)

    def _expand(self, plants, safe_soil, had_enemies):
        # Harvest Plants first: scale birth energy so baby always hits >= 580 after eating
        if plants:
            plants.sort(key=lambda item: item[1], reverse=True)
            plant_floor = 1800 if (had_enemies or not self.poison) else 1350
            for d, p_str in plants:
                birth_energy = max(1, 580 - int(p_str))
                if self.strength() > plant_floor + Propagator.USE_COST + birth_energy:
                    self.next_child_type = "zeus"
                    self.womb.give_birth(birth_energy, d)
                    self.expected_babies.add(d)
                else:
                    break

        if not safe_soil:
            return

        random.shuffle(safe_soil)
        # Spending down to 1320 when safe still recovers to 2000 cap next turn (+680/turn)
        soil_floor = 1900 if had_enemies else 1320
        pop = Zeus.instance_count()

        for d in safe_soil:
            # Periodically launch a Hermes mobile assassin/paratrooper during early-mid game
            if (
                not had_enemies
                and self.poison is not None
                and 12 <= pop < 4500
                and len(safe_soil) >= 2
                and self.strength() > 1350 + Propagator.USE_COST + 1100
                and random.random() < 0.045
            ):
                self.next_child_type = "hermes"
                self.womb.give_birth(1100, d)
                self.next_child_type = "zeus"
                continue

            # Standard high-speed Zeus baby (580 energy -> 2 PhotoGlands Turn 1, 5 by Turn 3)
            if self.strength() > soil_floor + Propagator.USE_COST + 580:
                self.next_child_type = "zeus"
                self.womb.give_birth(580, d)
                self.expected_babies.add(d)
            else:
                break

    def _scan_neighbors(self):
        enemies = []
        plants = []
        safe_soil = []
        cloaked_suspects = []
        ally_count = 0

        for d in ALL_DIRS:
            if self.strength() <= 20:
                break
            t = self.type_sensor.sense(d)

            if issubclass(t, Zeus):
                ally_count += 1
                self.expected_babies.discard(d)
            elif t is Plant:
                p_str = (
                    self.energy_sensor.sense(d)
                    if (self.energy_sensor and self.strength() > 15)
                    else 0
                )
                plants.append((d, p_str))
                self.expected_babies.discard(d)
            elif t is Soil:
                is_poison = (
                    self.poison_sensor.sense(d)
                    if (self.poison_sensor and self.strength() > 15)
                    else False
                )
                if is_poison:
                    self.expected_babies.discard(d)
                    continue
                if d in self.expected_babies:
                    cloaked_suspects.append(d)
                    self.expected_babies.discard(d)
                else:
                    safe_soil.append(d)
            else:
                self.expected_babies.discard(d)
                e_str = (
                    self.energy_sensor.sense(d)
                    if (self.energy_sensor and self.strength() > 15)
                    else 2000
                )
                # Ignore enemies already at <= 0 strength (already fatally poisoned)
                if e_str > 0:
                    enemies.append((d, e_str))

        self.last_enemy_dirs = [d for d, _ in enemies]
        self.last_non_ally_dirs = (
            self.last_enemy_dirs
            + cloaked_suspects
            + [d for d, _ in plants]
            + safe_soil
        )
        return enemies, plants, safe_soil, ally_count, cloaked_suspects

    def _top_up_poison(self, target_vol, min_keep_strength):
        if not self.poison:
            return
        needed = min(POISON_CAPACITY, target_vol) - self.poison.current_volume()
        if needed <= 0:
            return
        available = int(self.strength() - min_keep_strength)
        if available > 0:
            self.poison.add_poison(min(needed, available))

    def _snipe_enemy(self, direction, enemy_strength, min_keep_strength=150):
        if not self.poison:
            return
        # Drop enemy to <= -180 so even a first-slot PhotoGland (+150) cannot revive them
        dose = int((enemy_strength + 180) // 4) + 1
        dose = min(POISON_CAPACITY, max(50, dose))
        if self.poison.current_volume() < dose:
            self._top_up_poison(dose, min_keep_strength)
        vol_to_fire = min(dose, self.poison.current_volume())
        if vol_to_fire > 0:
            self.poison.drop_poison(direction, vol_to_fire)

    def _martyr_strike(self):
        if not self.poison:
            return
        vol = self.poison.current_volume()
        if vol <= 0:
            return
        targets = self.last_enemy_dirs if self.last_enemy_dirs else self.last_non_ally_dirs
        if not targets:
            return
        per_target = vol // len(targets)
        if per_target <= 0:
            self.poison.drop_poison(targets[0], vol)
        else:
            for d in targets:
                self.poison.drop_poison(d, per_target)


class Hermes(Zeus):
    """
    Mobile artillery assassin and paratrooper seeder (10 organs total, PhotoGlands-first):
      - 4 PhotoGlands (+600 energy/turn, processed first)
      - 1 Cilia
      - 1 CreatureTypeSensor
      - 1 PoisonSensor
      - 1 EnergySensor
      - 1 Propagator
      - 1 PoisonGland
      Net: +520 energy/turn once fully built.
    """

    def __init__(self):
        super().__init__()
        self.cilia = None
        self.heading = Direction.random()
        self.steps_from_home = 0

    def do_turn(self):
        if self.strength() <= 0:
            self._martyr_strike()
            return

        # Build all 4 PhotoGlands first on Turn 1 (1100 - 20 = 1080 -> 4 PhotoGlands, 80 left)
        while self.photo_count < 4 and self.strength() > PhotoGland.CREATION_COST + 5:
            PhotoGland(self)
            self.photo_count += 1

        if self.photo_count < 4:
            return

        self._grow_hermes_organs()

        if not self.type_sensor or self.strength() <= 30:
            return

        enemies, plants, safe_soil, ally_count, _ = self._scan_neighbors()

        # Priority 1: Drive-by artillery barrage on every adjacent live enemy
        if enemies and self.poison:
            enemies.sort(key=lambda item: item[1], reverse=True)
            for d, e_str in enemies:
                self._snipe_enemy(d, e_str, min_keep_strength=250)

        # Priority 2: Keep PoisonGland armor charged
        if self.poison:
            self._top_up_poison(POISON_CAPACITY, min_keep_strength=1300)

        # Priority 3: Drop a Zeus fortress seed far away from home
        if self.womb and self.poison and self.steps_from_home >= 5 and not enemies:
            if plants and self.strength() > 1650:
                plants.sort(key=lambda item: item[1], reverse=True)
                seed_dir, p_str = plants.pop(0)
                birth_energy = max(1, 580 - int(p_str))
                if self.strength() > 1350 + Propagator.USE_COST + birth_energy:
                    self.next_child_type = "zeus"
                    self.womb.give_birth(birth_energy, seed_dir)
                    self.steps_from_home = 0
            elif len(safe_soil) >= 3 and self.strength() > 1950:
                seed_dir = safe_soil.pop(0)
                self.next_child_type = "zeus"
                self.womb.give_birth(580, seed_dir)
                self.steps_from_home = 0

        # Priority 4: Move (prioritize Plants for free meals, then momentum cruising)
        if self.cilia and self.strength() > Cilia.USE_COST + 30:
            move_dir = None
            if plants:
                move_dir = max(plants, key=lambda item: item[1])[0]
            elif safe_soil:
                if self.heading in safe_soil and random.random() < 0.85:
                    move_dir = self.heading
                else:
                    back = self.heading.opposite()
                    forward_choices = [d for d in safe_soil if d != back]
                    move_dir = random.choice(forward_choices if forward_choices else safe_soil)
                    self.heading = move_dir

            if move_dir is not None:
                self.cilia.move_in_direction(move_dir)
                self.steps_from_home += 1
                self.expected_babies.clear()

    def _grow_hermes_organs(self):
        if not self.cilia and self.strength() > Cilia.CREATION_COST + 5:
            self.cilia = Cilia(self)
        if not self.type_sensor and self.strength() > CreatureTypeSensor.CREATION_COST + 5:
            self.type_sensor = CreatureTypeSensor(self)
        if not self.poison_sensor and self.strength() > PoisonSensor.CREATION_COST + 5:
            self.poison_sensor = PoisonSensor(self)
        if not self.energy_sensor and self.strength() > EnergySensor.CREATION_COST + 5:
            self.energy_sensor = EnergySensor(self)
        if not self.womb and self.strength() > Propagator.CREATION_COST + 5:
            self.womb = ZeusPropagator(self)
        if not self.poison and self.strength() > PoisonGland.CREATION_COST + 5:
            self.poison = PoisonGland(self)


class ZeusPropagator(Propagator):
    """Single propagator that spawns either Zeus or Hermes based on host state."""

    def make_child(self):
        if self.host().next_child_type == "hermes":
            return Hermes()
        return Zeus()