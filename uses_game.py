from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Game, HasGame
    import pygame as pg


class UsesGame:
    game: Game = None

    # should this have a default of None (or should None need to be passed explicitly)
    def __init__(self, game: HasGame | None, strict=True):
        self.set_game(game, strict, '__init__')

    def set_game(self, game: HasGame | None, strict=True, method_name='set_game'):
        if isinstance(game, UsesGame):
            game = game.game
        self.game = game or self.game
        if strict and self.game is None:
            raise RuntimeError(
                f"game needs to be specified when using strict=True "
                f"(either as an attribute before calling "
                f"{method_name} or passed as an argument)")

    @property
    def curr_tick(self):
        return self.game.curr_tick

    @property
    def display_group(self) -> pg.sprite.AbstractGroup:
        return self.game.display_group

    @property
    def root_group(self) -> pg.sprite.AbstractGroup:
        return self.game.root_group

    @property
    def player(self):
        return self.game.player

    @property
    def fonts(self):
        return self.game.fonts

    @property
    def screen(self):
        return self.game.screen

    @property
    def log(self):
        return self.game.log
