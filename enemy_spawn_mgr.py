from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pygame import Vector2 as Vec2

from enemy import EnemyWithHealth
from uses_game import UsesGame

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

    @classmethod
    def make_random(cls, spawner: EnemySpawnMgr):
        return cls(spawner).randomize()

    @abstractmethod
    def randomize(self):
        """Randomizes this instance **inplace**!, returns self"""

    @abstractmethod
    def spawn(self):
        ...

    @abstractmethod
    def get_cost(self) -> float:
        ...

    def __str__(self):
        return f'{type(self).__qualname__}'


class SingleEnemySpawn(EnemySpawnStrategy):
    def __init__(self, spawner: EnemySpawnMgr, health: int = 1):
        super().__init__(spawner)
        self.spawner = spawner
        self.health = health

    def randomize(self):
        """Randomizes this instance **inplace**!, returns self"""
        target_health = math.sqrt(self.spawner.strength * 40)
        health = random.uniform(1, target_health * 2)
        self.game.log.debug(f"Next SingleEnemySpawn has {health=:.2f} "
                            f"~ uniform(1, {target_health * 2:.2f})")
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
