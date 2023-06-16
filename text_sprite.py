from __future__ import annotations

from typing import TYPE_CHECKING

import pygame as pg

from sprite_bases import RectUpdatingSprite

if TYPE_CHECKING:
    from main import HasGame

Vec2 = pg.Vector2


class TextSprite(RectUpdatingSprite):
    pos: Vec2 = None
    text: str = None
    always_render = False

    def __init__(self, game: HasGame | None, text: str, pos: Vec2 = None):
        self.set_game(game, method_name='__init__')
        self.pos = pos or self.pos
        self.set_text(text)
        super().__init__(None)

    def set_text(self, text: str):
        if text != self.text or self.surf is None or self.always_render:
            self.text = text
            self.set_surf(self.render_text())
        if self.surf is None:
            raise RuntimeError("surface was not been returned from"
                               " render_text or wasn't set by set_surf")
        self.update_rect()

    def update_rect(self):
        self.rect = self.get_rect()
        if self.rect is None:
            raise RuntimeError("rect was not returned from get_rect")
        self.size = self.rect.size

    def render_text(self) -> pg.Surface:
        raise NotImplementedError("You should override render_text when using TextSprite")

    def get_rect(self) -> pg.Rect:
        """This should recalculate not just the rect but also the pos"""
        raise NotImplementedError("You should override get_rect when using TextSprite")
