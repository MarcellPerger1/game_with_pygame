from __future__ import annotations

from typing import TYPE_CHECKING

import pygame as pg

from sprite_bases import DrawableSprite

if TYPE_CHECKING:
    from main import HasGame

Vec2 = pg.Vector2


class TextSprite(DrawableSprite):
    pos: Vec2 = None
    text: str = None
    always_render = False

    def __init__(self, game: HasGame | None, text: str, pos: Vec2 = None):
        super().__init__(game)
        self.pos = pos or self.pos
        self.set_text(text)

    def set_text(self, text: str):
        if text != self.text or self.surf is None or self.always_render:
            self.text = text
            self.set_surf(self.render_text())
        if self.surf is None:
            raise RuntimeError("surface was not been returned from"
                               " render_text or wasn't set by set_surf")
        self.rect = self.get_rect()
        if self.rect is None:
            raise RuntimeError("rect was not returned from get_rect")

    def render_text(self) -> pg.Surface:
        raise NotImplementedError("You should override render_text when using TextSprite")

    def get_rect(self) -> pg.Rect:
        raise NotImplementedError("You should override get_rect when using TextSprite")
