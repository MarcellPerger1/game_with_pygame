from __future__ import annotations

import cProfile
import logging as lg
import random
import sys
import time
from typing import Any, overload, Union, TextIO

import pygame as pg
from pygame import Vector2 as Vec2

from bullet import Bullet
from collectable import TurretItem
from containers import HasRect
from enemy import CommonEnemy, EnemyWithHealth
from perf import PerfMgr
from pg_util import render_text
from sprite_bases import CommonSprite, RectUpdatingSprite
from text_sprite import TextSprite
from trigger_once import trigger_once
from turret import Turret, TurretRangeIndicator
from uses_game import UsesGame
from util import option

USE_FLIP = True
ALLOW_CHEATS = True

FPS = 60
SPEED = 3.8
P_RADIUS = 20
SPAWN_INTERVAL_START = 65
SPAWN_ENEMY_DELAY_START = 75
MAX_ENEMIES_PER_TICK = 18
MIN_SPAWN_INTERVAL = 0.01


class PGExit(BaseException):
    pass


class EnemySpawnMgr(UsesGame):
    def __init__(self, game_: HasGame):
        super().__init__(game_)
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


class Fonts:
    huge: pg.font.Font
    monospace: pg.font.Font

    @classmethod
    def init(cls):
        cls.huge = pg.font.SysFont('Helvetica', 200, bold=True)
        cls.monospace = pg.font.SysFont('monospace', 18)


class GameLogger(lg.Logger):
    def __init__(self, stream: TextIO = None):
        super().__init__("game_with_pygame", lg.INFO)
        if stream is None:
            stream = sys.stderr
        self._stream_handler = lg.StreamHandler(stream)
        self._formatter = lg.Formatter('[{levelname}] {message}', style='{')
        self._stream_handler.setFormatter(self._formatter)
        self.addHandler(self._stream_handler)


class Game:
    curr_tick: int
    frame_start: float
    frame_end: float
    frame_time: float

    def __init__(self, init=False):
        self.is_init = False
        if init:
            self.init()

    def init(self):
        self._init_logger()
        self._init_pygame()
        self._init_timing()
        self._init_fonts()
        self._init_groups()
        self._init_window()
        self._init_components()
        self._init_objects()

    def _init_logger(self):
        # this way of initializing is not recommended but I'm doing it anyway
        # as it's the cleanest way (when using a separate class)
        self.log = GameLogger()
        self.log.info("Logger initialized")

    # noinspection PyMethodMayBeStatic
    def _init_pygame(self):
        self.log.info('Initializing modules')
        n_pass, n_fail = pg.init()
        self.log.info(f'Initialized modules: {n_pass} successes, {n_fail} fails')

    def _init_fonts(self):
        self.log.info('Initializing fonts')
        t0 = time.perf_counter()
        self.fonts = Fonts()
        self.fonts.init()
        t1 = time.perf_counter()
        self.log.info(f'Initialized fonts in {t1 - t0:.2f}s')

    def _init_timing(self):
        self.log.info('Initializing clock')
        self.curr_tick = 0
        self.clock = pg.time.Clock()

    def _init_groups(self):
        self.log.info('Initializing groups')
        self.root_group = pg.sprite.Group()
        # todo should use LayeredUpdates / LayeredDirty
        self.display_group = pg.sprite.RenderUpdates()
        self.enemies = pg.sprite.Group()
        self.turret_range_overlays = pg.sprite.Group()
        self.bullets = pg.sprite.Group()
        self.turrets = pg.sprite.Group()

    def _init_window(self):
        self.log.info('Initializing window')
        self.screen = pg.display.set_mode((1600, 900), pg.RESIZABLE, display=0)
        self.dirty_this_frame: list[pg.Rect] = []
        self._clear_window()

    def _clear_window(self):
        self.log.info('Clearing window')
        self.screen.fill((255, 255, 255))
        pg.display.flip()

    def _init_objects(self):
        self.log.info('Initializing objects')
        self.player = Player(self, Vec2(700, 400))
        TurretItem(self, Vec2(400, 600))
        self.initial_enemy = EnemyWithHealth(self, Vec2(50, 655), 1, immobile=True)
        self.turrets_text = TurretsText(self)
        self.fps_text = FpsText(self, "FPS: N/A")
        self.enemy_info_text = EnemyInfoText(self)

    def _init_components(self):
        self.log.info('Initializing components')
        self.enemy_spawner = EnemySpawnMgr(self)
        self.perf_mgr = PerfMgr()
        self.tutorial = Tutorial(self)

    def mainloop_inner(self):
        while True:
            self.do_one_frame()
            self.wait_for_next_frame()

    def mainloop(self):
        try:
            self.mainloop_inner()
        except PGExit:
            pass
        self.close_window()

    def close_window(self):
        self.pre_quit()
        pg.quit()
        self.post_quit()

    def pre_quit(self):
        pass

    def post_quit(self):
        if self.perf_mgr.mem_snapshot:
            self.perf_mgr.print_snapshot()

    def do_one_frame(self):
        self.perf_mgr.curr_cpu_profile = None
        self.init_frame()
        self.handle_events()
        self.frame_inner_with_prof(self.perf_mgr.curr_cpu_profile)
        self.after_frame()

    def init_frame(self):
        self.screen.fill((255, 255, 255))
        self.dirty_this_frame.clear()
        self.frame_start = time.perf_counter()

    def after_frame(self):
        self.frame_end = time.perf_counter()
        self.frame_time = self.frame_end - self.frame_start
        if self.curr_tick % 10 == 1:
            self.log.debug(f'Update took: {self.frame_time * 1000:.2f}ms')
            self.log.debug(f'FPS: {self.clock.get_fps():.2f}')

    def wait_for_next_frame(self):
        self.clock.tick(FPS)
        self.curr_tick += 1

    def frame_inner_with_prof(self, p: cProfile.Profile | None):
        if not p:
            return self.do_frame_inner()
        with p:
            self.do_frame_inner()
        p.dump_stats('game_perf.prof')

    def do_frame_inner(self):
        self.do_tick()
        self.draw_objects()

    def draw_objects(self):
        if USE_FLIP:
            self.display_group.draw(self.screen)
            TurretRangeIndicator.draw_all(self)
            pg.display.flip()
        else:
            dirty = self.display_group.draw(self.screen)
            TurretRangeIndicator.draw_all(self)
            dirty += self.dirty_this_frame
            pg.display.update(dirty)

    def do_tick(self):
        if self.player.is_dead:
            return
        self.root_group.update()
        self.on_post_tick()

    def on_post_tick(self):
        self.enemy_spawner.handle_enemy_spawns()

    def on_player_die(self):
        GameOver(self, f'Game Over\nScore: {self.player.enemies_killed}')
        self.log.info("Game over")

    # todo observer pattern for on_* methods
    def on_kill_enemy(self, enemy, bullet):
        self.enemy_spawner.increment_interval_once()
        self.player.on_kill_enemy(enemy, bullet)

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.perf_mgr.take_snapshot()
                raise PGExit
            if event.type == pg.KEYDOWN and event.key == pg.K_p:
                self.perf_mgr.take_cpu_profile()
            if event.type == pg.KEYDOWN and event.key == pg.K_t and ALLOW_CHEATS:
                self.player.turrets += 20
                self.turrets_text.update()
            if event.type == pg.VIDEORESIZE:
                self.on_resize(event)

    def on_resize(self, event):
        t0 = time.perf_counter()
        self.update_ui_position(event.size)
        TurretRangeIndicator.make_overlay_surf(self, force_remake=True)
        t1 = time.perf_counter()
        self.log.info(f"Resized window to {event.w}x{event.h} in {t1 - t0:.3f}s")

    def update_ui_position(self, _new_size: Vec2):
        for s in self.display_group:
            if isinstance(s, RectUpdatingSprite):
                s.update_rect()

    @property
    def ticks(self):
        return self.curr_tick

    @ticks.setter
    def ticks(self, value: int):
        self.curr_tick = value


HasGame = Union[UsesGame, Game]


class EveryNTicks(UsesGame):
    def __init__(self, game_: HasGame, n: int, offset=1):
        super().__init__(game_)
        self.n = n
        self.started_at = self.curr_tick + offset

    def is_this_frame(self):
        return (self.curr_tick >= self.started_at
                and (self.curr_tick - self.started_at) % self.n == 0)


class Player(CommonSprite):
    size = Vec2(P_RADIUS * 2, P_RADIUS * 2)

    def __init__(self, game: HasGame, pos: Vec2):
        super().__init__(game, pos)
        self._turrets = 0.0
        self.is_dead = False
        self.enemies_killed = 0

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
            self.set_pos(self.pos + m)

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
                self.game.turrets_text.update()

    def on_kill_enemy(self, _enemy: CommonEnemy, _bullet: Bullet):
        self.enemies_killed += 1
        self.turrets += 0.2

    def die(self):
        self.is_dead = True
        self.game.on_player_die()


class GameOver(TextSprite):
    def __init__(self, game: HasGame, text: str):
        super().__init__(game, text)

    def render_text(self) -> pg.Surface:
        return render_text(self.fonts.huge, self.text, color='black', justify='center')

    def get_rect(self) -> pg.Rect:
        self.pos = self.screen.get_rect().center
        return self.surf.get_rect(center=self.pos)


class TurretsText(TextSprite):
    def __init__(self, game: HasGame, text: str = None):
        text = option(text, 'Turrets: 0')
        super().__init__(game, text)
        self.set_text(text)

    def render_text(self) -> pg.Surface:
        return self.fonts.monospace.render(self.text, True, 'black')

    def get_rect(self) -> pg.Rect:
        self.pos = Vec2(5, 5)
        return self.surf.get_rect(topleft=self.pos)

    @overload
    def update(self): ...

    def update(self, *args: Any, **kwargs: Any) -> None:
        self.set_text(f'Turrets: {self.player.turrets}')


class EnemyInfoText(TextSprite):
    def __init__(self, game: HasGame):
        super().__init__(game, "(Loading enemy info...)", )

    def render_text(self) -> pg.Surface:
        return render_text(self.fonts.monospace, self.text, True, 'black')

    def get_rect(self) -> pg.Rect:
        extra_y = self.fonts.monospace.get_height() * 2
        self.pos = Vec2(5, 5) + Vec2(0, extra_y)
        return self.surf.get_rect(topleft=self.pos)

    def update(self, *args: Any, **kwargs: Any) -> None:
        spawn_interval = self.game.enemy_spawner.enemy_spawn_interval
        self.set_text(f'Enemies killed: {self.player.enemies_killed}\n'
                      f'Enemies currently alive: {len(self.game.enemies)}\n'
                      f'Enemy spawn interval: {spawn_interval:.3f}')


class FpsText(TextSprite):
    def __init__(self, game: HasGame, text: str):
        super().__init__(game, text)

    def render_text(self) -> pg.Surface:
        return render_text(self.fonts.monospace, self.text, True,
                           pg.color.Color('black'), justify='right')

    def get_rect(self) -> pg.Rect:
        self.pos = Vec2(self.screen.get_width() - 5, 5)
        return self.surf.get_rect(topright=self.pos)

    def update(self, *args: Any, **kwargs: Any) -> None:
        if self.curr_tick % 5 == 1:
            self.set_text(f'FPS: {self.game.clock.get_fps():>5.2f}\n'
                          f'ms/frame: {self.game.frame_time*1000:>5.2f}')


class Tutorial(UsesGame):
    def __init__(self, game: Game | UsesGame):
        super().__init__(game)

    @trigger_once
    def place_turret(self):
        self.game.enemy_spawner.is_enabled = True
        self.game.initial_enemy.immobile = False


def main():
    print('Hello world')
    game = Game()
    game.init()
    game.mainloop()


if __name__ == '__main__':
    main()
