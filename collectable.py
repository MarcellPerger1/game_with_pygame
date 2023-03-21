from __future__ import annotations

from typing import Any, TYPE_CHECKING

import pygame as pg
from pygame import Vector2 as Vec2

from sprite_bases import CommonSprite

if TYPE_CHECKING:
    from main import HasGame


class Collectable(CommonSprite):
    size = Vec2(12, 12)  # 'standard' size for a collectable; override this

    def __init__(self, game: HasGame, pos: Vec2):
        super().__init__(game, pos)

    # noinspection PyMethodMayBeStatic
    def on_collect(self):
        """This method is called when this has been collected (after being kill-ed)"""

    def update(self, *args: Any, **kwargs: Any) -> None:
        if pg.sprite.collide_rect(self, self.player):
            self.kill()
            self.on_collect()


class TurretItem(Collectable):
    def draw_sprite(self):
        pg.draw.rect(self.surf, 'darkolivegreen3', self.surf.get_rect())

    def on_collect(self):
        self.player.turrets += 1
        self.game.turrets_text.update()
