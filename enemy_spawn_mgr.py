from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from math import pi
from typing import TYPE_CHECKING

from pygame import Vector2 as Vec2

from enemy import EnemyWithHealth
from pg_util import vec2_from_polar
from uses_game import UsesGame
from util import uniform_from_mean, clamp

if TYPE_CHECKING:
    from main import HasGame


class EnemySpawnStrategy(UsesGame, ABC):
    def __init__(self, spawner: EnemySpawnMgr):
        """The __init__ of all subclasses should be compatible
        with this signature i.e. should be able to accept creation
        like <subclass>(spawner), the other arguments should be optional.
        This is needed for `make_random` to work.
        Alternatively, just override `make_random`"""
        super().__init__(spawner)
        self.spawner = spawner

    @classmethod
    def make_random(cls, spawner: EnemySpawnMgr):
        self = cls(spawner)
        self.randomize()
        return self

    @abstractmethod
    def randomize(self) -> EnemySpawnStrategy:
        """Randomizes this instance **inplace**!, returns self"""

    @abstractmethod
    def spawn(self) -> EnemyWithHealth | list[EnemyWithHealth]:
        ...

    @abstractmethod
    def get_cost(self) -> float:
        ...

    def __str__(self):
        return f'{type(self).__qualname__}'


class SingleEnemySpawn(EnemySpawnStrategy):
    def __init__(self, spawner: EnemySpawnMgr, health: int = 1):
        super().__init__(spawner)
        self.health = health

    def randomize(self):
        """Randomizes this instance **inplace**!, returns self"""
        mean_health = self.spawner.base_enemy_health
        health = random.uniform(1, mean_health * 2)
        self.game.log.debug(f"Next SingleEnemySpawn has {health=:.2f} "
                            f"~ uniform(1, {mean_health * 2:.2f})")
        self.health = round(health)
        return self

    def spawn(self):
        angle = random.uniform(0, 360)
        distance = random.uniform(250, 500)
        at = Vec2()
        at.from_polar((distance, angle))
        at += Vec2(self.player.pos)
        return EnemyWithHealth(self, at, self.health)

    def get_cost(self) -> float:
        return self.health

    def __str__(self):
        return f'{type(self).__qualname__} with health={self.health}'


class ClusterEnemySpawn(EnemySpawnStrategy):
    def __init__(self, spawner: EnemySpawnMgr):
        super().__init__(spawner)
        self.total_health = 0
        self.enemy_health_list = []

    def randomize(self):
        total_health = self.spawner.base_enemy_health * 2.5
        mean_amount = self.spawner.strength * 3.0
        amount = round(random.uniform(mean_amount * 0.7, mean_amount * 1.3))
        amount = clamp(amount, 2, None)
        mean_health = total_health / amount
        health_min = math.floor(mean_health) - 1
        health_max = math.ceil(mean_health) + 1
        self.enemy_health_list = [
            random.uniform(health_min, health_max) for _ in range(amount)]
        self.total_health = sum(self.enemy_health_list)
        return self

    def spawn(self):
        mean_distance = random.uniform(250, 500)
        distance_variation = random.uniform(70, 170)
        mean_angle = random.uniform(0, 360)
        angle_length_variation = random.uniform(150, 250)
        # length / circumference = angle / 360
        # angle = 360*length / (2*pi*r) = 180*length / (pi*r)
        angle_variation = 180 * angle_length_variation / (pi * mean_distance)
        enemies = []
        for health in self.enemy_health_list:
            angle = uniform_from_mean(mean_angle, angle_variation)
            distance = uniform_from_mean(mean_distance, distance_variation)
            if distance < 250:
                distance = random.uniform(
                    250, mean_distance + distance_variation)
            pos = vec2_from_polar((distance, angle))
            pos += self.player.pos
            enemies.append(EnemyWithHealth(self, pos, health))
        return enemies

    def get_cost(self) -> float:
        return self.total_health


class EnemySpawnMgr(UsesGame):
    next_enemy: EnemySpawnStrategy

    def __init__(self, game: HasGame, strength=0.005, enabled=False, start_points=0.0):
        super().__init__(game)
        self.points = start_points
        self.strength = strength
        self.enabled = enabled
        self.enable_after: int | None = None
        self.decide_next_enemy()

    def enable(self, delay: int = 0):
        self.enable_after: int | None = self.curr_tick + delay
        self.check_if_should_enable()

    def check_if_should_enable(self):
        if self.enable_after is not None and self.curr_tick >= self.enable_after:
            self.enabled = True

    def decide_next_enemy(self):
        cluster_chance = clamp(self.strength * 0.5, None, 0.35)
        if self.strength > 0.2 and random.random() < cluster_chance:
            self.next_enemy = ClusterEnemySpawn.make_random(self)
        else:
            self.next_enemy = SingleEnemySpawn.make_random(self)

    def on_tick(self):
        self.check_if_should_enable()
        if not self.enabled:
            return
        self.points += self.strength
        self.strength += 0.0001 / 60
        self.spawn_all()

    def on_kill_enemy(self, enemy: EnemyWithHealth):
        if not self.enabled:
            return
        self.strength += 0.0006 + enemy.max_hp * 0.0004

    @property
    def base_enemy_health(self):
        return math.sqrt(self.strength * 40)

    def spawn_all(self):
        while self.points >= self.next_enemy.get_cost():
            self.spawn_from_obj(self.next_enemy)

    def spawn_from_obj(self, o: EnemySpawnStrategy):
        cost = o.get_cost()
        assert self.points >= cost
        o.spawn()
        self.game.log.debug(f"Spawned {o!s}")
        self.points -= cost
        self.decide_next_enemy()
