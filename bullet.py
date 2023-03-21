from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pygame as pg
from pygame.math import Vector2 as Vec2

from sprite_bases import CommonSprite

if TYPE_CHECKING:
    from main import HasGame
    from enemy import CommonEnemy

SHOW_BULLETS = True  # todo test the effect of this on performance
BULLET_SPEED = 25


class Bullet(CommonSprite):
    size = Vec2(6, 6)

    def __init__(self, game: HasGame, pos: Vec2, target: Vec2,
                 *groups: pg.sprite.AbstractGroup):
        self.set_game(game)
        super().__init__(None, pos, self.game.bullets, *groups, in_display=SHOW_BULLETS)
        self.target = target

    def draw_sprite(self):
        if SHOW_BULLETS:
            pg.draw.rect(self.surf, 'red4', self.surf.get_rect())
        else:
            # use less memory, as it can now free self.surf
            # (set in CommonSprite.__init__)
            self.surf = self.image = None

    def on_hit_enemy(self, enemy: CommonEnemy):
        enemy.on_hit_by_bullet(self)
        self.kill()

    def update(self, *args: Any, **kwargs: Any) -> None:
        enemy: CommonEnemy | None = pg.sprite.spritecollideany(self, self.game.enemies)
        if enemy is not None:
            self.on_hit_enemy(enemy)
            return
        if self.pos == self.target:
            self.kill()
        self.pos = self.pos.move_towards(self.target, BULLET_SPEED)
        self.rect.center = self.pos
