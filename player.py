from __future__ import annotations

from typing import Any, TYPE_CHECKING

import pygame as pg
from pygame import Vector2 as Vec2

from bullet import Bullet
from containers import HasRect
from enemy import EnemyWithHealth
from sprite_bases import CommonSprite
from turret import Turret

if TYPE_CHECKING:
    from main import HasGame

SPEED = 3.8
P_RADIUS = 20


class Player(CommonSprite):
    size = Vec2(P_RADIUS * 2, P_RADIUS * 2)

    def __init__(self, game: HasGame, pos: Vec2):
        super().__init__(game, pos)
        self._turrets = 0.0
        self.is_dead = False
        self.enemies_killed = 0
        self.score = 0

    @property
    def turrets(self):
        return self._turrets

    @turrets.setter
    def turrets(self, value: float):
        # rounding because of fp precision, 0.1 + 0.2 != 0.3
        # (don't want to end up with 0.999999...4 turrets)
        self._turrets = round(value, 8)
        self.game.turrets_text.update()

    def draw_sprite(self):
        pg.draw.circle(self.surf, 'blue', self.size / 2, P_RADIUS)

    def handle_movement(self):
        keys = pg.key.get_pressed()
        m = Vec2()
        if keys[pg.K_DOWN] or keys[pg.K_s]:
            m += Vec2(0, 1)
        if keys[pg.K_UP] or keys[pg.K_w]:
            m += Vec2(0, -1)
        if keys[pg.K_LEFT] or keys[pg.K_a]:
            m += Vec2(-1, 0)
        if keys[pg.K_RIGHT] or keys[pg.K_d]:
            m += Vec2(1, 0)
        if m.length_squared() != 0:
            m = m.normalize() * SPEED
            self.pos += m

    def update(self, *args: Any, **kwargs: Any) -> None:
        self.handle_movement()
        mouse = pg.mouse.get_pressed()
        if mouse[0]:
            self.while_left_click()

    def while_left_click(self):
        if self.turrets >= 1.0:
            mouse_pos = Vec2(pg.mouse.get_pos())
            if not pg.sprite.spritecollide(
                    HasRect(Turret.get_virtual_rect(mouse_pos)),
                    self.game.turrets, False):
                Turret(self, mouse_pos)
                self.turrets -= 1

    def on_kill_enemy(self, enemy: EnemyWithHealth, _bullet: Bullet):
        self.enemies_killed += 1
        self.turrets += 0.165 + 0.035 * enemy.max_hp
        self.score += int(enemy.max_hp)

    def die(self):
        self.is_dead = True
        self.game.on_player_die()
