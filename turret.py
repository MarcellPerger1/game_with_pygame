from __future__ import annotations

from typing import Any, Literal, TYPE_CHECKING

import pygame as pg
from pygame import Vector2 as Vec2

from bullet import Bullet
from pg_util import nearest_of_group
from sprite_bases import CommonSprite

if TYPE_CHECKING:
    from main import HasGame, Game
    from enemy import CommonEnemy

SHOW_TURRET_RANGE = True
TURRET_INTERVAL = 45
TURRET_RANGE = 140


class Turret(CommonSprite):
    size = Vec2(20, 20)

    def __init__(self, game: HasGame, pos: Vec2, *groups: pg.sprite.AbstractGroup,
                 interval: int = TURRET_INTERVAL):
        self.set_game(game)
        super().__init__(None, pos, self.game.turrets, *groups)
        self.interval = interval
        self.shot_on_tick = None
        if SHOW_TURRET_RANGE:
            TurretRangeIndicator(self, self.pos)
        self.game.tutorial.place_turret()

    def draw_sprite(self):
        pg.draw.rect(self.surf, 'darkgreen', self.surf.get_rect())

    def can_shoot(self):
        return (self.shot_on_tick is None
                or self.curr_tick >= self.shot_on_tick + self.interval)

    def update(self, *args: Any, **kwargs: Any) -> None:
        if self.can_shoot():
            target: CommonEnemy = nearest_of_group(self.pos, self.game.enemies)
            if target is not None and self.can_shoot_enemy(target):
                Bullet(self, self.pos, target.pos)
                self.shot_on_tick = self.curr_tick

    def can_shoot_enemy(self, enemy: CommonEnemy):
        return self.pos.distance_squared_to(enemy.pos) <= TURRET_RANGE * TURRET_RANGE


class TurretRangeIndicator(CommonSprite):
    size = Vec2(TURRET_RANGE * 2, TURRET_RANGE * 2)
    common_surf: pg.surface.Surface = None
    """The surface that is drawn for each overlay"""

    need_redraw: list[TurretRangeIndicator] | Literal['all'] = 'all'
    overlays_surf: pg.Surface = None

    def __init__(self, game: HasGame, pos: Vec2, *groups: pg.sprite.AbstractGroup):
        self.set_game(game)
        super().__init__(None, pos, self.game.turret_range_overlays, *groups,
                         in_display=False)
        self.on_create()

    def make_surface(self):
        if self.common_surf is None:
            self.make_common_surf()
        return self.common_surf

    def make_common_surf(self):
        self.common_surf = pg.surface.Surface(self.size, pg.SRCALPHA)
        pg.draw.circle(self.common_surf, pg.color.Color(0, 255, 0, 60),
                       self.size / 2, TURRET_RANGE)

    def draw_overlay(self, target: pg.surface.Surface):
        return target.blit(self.surf, self.rect, None, special_flags=pg.BLEND_RGBA_MAX)

    def draw_sprite(self):
        pass  # already draw when surface created

    def on_create(self):
        self.game.dirty_this_frame.append(self.rect)
        self.request_redraw(self)

    @classmethod
    def request_redraw(cls, *args: TurretRangeIndicator):
        if cls.need_redraw == 'all':
            return
        if 'all' in args:
            cls.need_redraw = 'all'
        cls.need_redraw += args

    @classmethod
    def make_overlay_surf(cls, game: Game, remake_force=False):
        if cls.overlays_surf is None or remake_force:
            cls.overlays_surf = pg.Surface(game.screen.get_size(), pg.SRCALPHA)

    @classmethod
    def draw_all(cls, game: Game):
        cls.update_overlays_surf(game)
        cls.blit_all(game)

    @classmethod
    def update_overlays_surf(cls, game: Game):
        if not cls.need_redraw or not SHOW_TURRET_RANGE:
            return
        cls.make_overlay_surf(game)
        if cls.need_redraw == 'all':
            cls.overlays_surf.fill((0, 0, 0, 0))
            for t in game.turret_range_overlays:
                t: TurretRangeIndicator
                t.draw_overlay(cls.overlays_surf)
        else:
            for t in cls.need_redraw:
                t.draw_overlay(cls.overlays_surf)
        cls.need_redraw = []

    @classmethod
    def blit_all(cls, game: Game):
        return game.screen.blit(cls.overlays_surf, game.screen.get_rect())
