from __future__ import annotations

import random
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


class EnemySpawnMgr2(UsesGame):
    next_enemy_health: int

    def __init__(self, game: HasGame, strength=0.01, enabled=False, start_points=0.0):
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
        desired_wait_time = 60  # ticks
        health_after_wait_time = desired_wait_time * self.strength
        if health_after_wait_time <= 1.0:
            health_after_wait_time = 1.0
        health = random.triangular(1, health_after_wait_time * 2)
        self.next_enemy_health = round(health)

    def on_tick(self):
        self.check_if_should_enable()
        if not self.enabled:
            return
        self.points += self.strength
        self.strength += 0.0005 / 60
        while self.points >= self.next_enemy_health:
            self.spawn_enemy()

    def on_kill_enemy(self, enemy: EnemyWithHealth):
        if not self.enabled:
            return
        self.strength += enemy.health * 0.005

    def spawn_enemy(self):
        angle = random.uniform(0, 360)
        distance = random.uniform(250, 500)
        at = Vec2()
        at.from_polar((distance, angle))
        at += Vec2(self.player.pos)
        health = self.next_enemy_health
        EnemyWithHealth(self, at, health)
        self.points -= health
        self.decide_next_enemy()


class EnemySpawnMgr(UsesGame):
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
