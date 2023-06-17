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


SPAWN_INTERVAL_START = 65
SPAWN_ENEMY_DELAY_START = 75
MAX_ENEMIES_PER_TICK = 18
MIN_SPAWN_INTERVAL = 0.01


class EnemySpawnStrategy(UsesGame, ABC):
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
        self.game.log.debug(f"Next enemy has {health=:.2f} "
                            f"~ uniform(1, {target_health * 2:.2f})")
        self.health = round(health)
        return self

    @classmethod
    def make_random(cls, spawner: EnemySpawnMgr):
        return cls(spawner).randomize()

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


class _EnemySpawnMgrOld(UsesGame):
    def __init__(self, game: HasGame):
        super().__init__(game)
        self.is_enabled = False
        self.next_enemy_time: int | None = None
        self.enemy_spawn_interval: float = SPAWN_INTERVAL_START

    def handle_enemy_spawns(self):
        if not self.is_enabled:
            return
        if self.next_enemy_time is None:
            self.next_enemy_time = self.curr_tick + SPAWN_ENEMY_DELAY_START
        self.spawn_enemies()

    def spawn_enemies(self):
        enemies_this_tick = 0
        while (self.next_enemy_time <= self.curr_tick
               and enemies_this_tick < MAX_ENEMIES_PER_TICK):
            self.spawn_enemy()
            self.next_enemy_time += self.enemy_spawn_interval
            enemies_this_tick += 1
        # if it would've spawned an extra enemy, set the next enemy time to the current time
        # (won't spawn it this frame but still allows spawning a lot next frame)
        # should really be `ticks + epsilon` as next enemy should spawn at the very start
        # of the next frame but we aren't spawning extra enemies this frame anyway.
        if self.next_enemy_time < self.curr_tick:
            self.next_enemy_time = self.curr_tick

    def get_interval_decrease(self):
        curr_val = self.enemy_spawn_interval
        return (0.980 if curr_val > 4.0 else
                0.990 if curr_val > 2.0 else
                0.994 if curr_val > 0.9 else
                0.997 if curr_val > 0.5 else
                0.9993 if curr_val > 0.25 else
                0.9998 if curr_val > 0.12 else
                0.99993 if curr_val > 0.06 else
                0.99998)

    def increment_interval_once(self):
        self.enemy_spawn_interval *= self.get_interval_decrease()
        if self.enemy_spawn_interval < MIN_SPAWN_INTERVAL:
            self.enemy_spawn_interval = MIN_SPAWN_INTERVAL

    def spawn_enemy(self):
        angle = random.uniform(0, 360)
        distance = random.uniform(250, 500)
        at = Vec2()
        at.from_polar((distance, angle))
        at += Vec2(self.player.pos)
        EnemyWithHealth(self, at, 1)
