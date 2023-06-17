from __future__ import annotations

from typing import Any, TYPE_CHECKING

import pygame as pg
from pygame import Vector2 as Vec2

from bullet import Bullet
from sprite_bases import CommonSprite

if TYPE_CHECKING:
    from main import HasGame

ENEMY_SPEED = 2.3


class CommonEnemy(CommonSprite):
    def __init__(self, game: HasGame, pos: Vec2,
                 *groups: pg.sprite.AbstractGroup,
                 is_in_enemies=True, **kwargs):
        self.set_game(game)
        groups = (*groups, self.game.enemies) if is_in_enemies else groups
        super().__init__(None, pos, *groups, **kwargs)

    def on_hit_by_bullet(self, bullet: Bullet):
        self.kill()
        self.game.on_kill_enemy(self, bullet)

    def on_collide_player(self):
        self.player.die()

    def update(self, *args: Any, **kwargs: Any) -> None:
        """This update function handles killing player on contact"""
        if pg.sprite.collide_rect(self, self.player):
            self.on_collide_player()


class EnemyWithHealth(CommonEnemy):
    size = Vec2(30, 30)

    def __init__(self, game: HasGame, pos: Vec2, health: float,
                 speed: float = ENEMY_SPEED, immobile=False):
        super().__init__(game, pos)
        self.health = self.max_hp = health
        self.immobile = immobile
        self.speed = speed

    def draw_sprite(self):
        pg.draw.rect(self.surf, 'red', self.surf.get_rect())

    def on_hit_by_bullet(self, bullet: Bullet):
        self.health -= 1
        self.check_dead(bullet)

    def check_dead(self, damage_source: Bullet | Any):
        if round(self.health, 9) > 0:
            return
        if self.is_damage_by_player(damage_source):
            self.kill_by_player(damage_source)
        else:
            self.kill()

    def kill_by_player(self, bullet: Bullet):
        self.game.on_kill_enemy(self, bullet)
        self.kill()

    @classmethod
    def is_damage_by_player(cls, damage: Bullet | Any):
        if isinstance(damage, Bullet):
            return True
        return False

    def handle_movement(self):
        if self.immobile:
            return
        self.pos = self.pos.move_towards(self.player.pos, self.speed)

    def update(self, *args: Any, **kwargs: Any) -> None:
        super().update(*args, **kwargs)
        self.handle_movement()
