from __future__ import annotations

import logging as lg
import sys
import time
from typing import Any, overload, Union, TextIO

import pygame as pg
from pygame import Vector2 as Vec2

from collectable import TurretItem
from enemy import EnemyWithHealth
from enemy_spawn_mgr import EnemySpawnMgr
from perf import DEBUG_MEMORY, DEBUG_CPU, MemProf, CpuProfileContextManager
from pg_util import render_text
from player import Player
from sprite_bases import RectUpdatingSprite
from text_sprite import TextSprite
from trigger_once import trigger_once
from turret import TurretRangeIndicator
from uses_game import UsesGame
from util import option

USE_FLIP = True
ALLOW_CHEATS = True

FPS = 60


class PGExit(BaseException):
    pass


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
    want_cpu_prof: bool = False

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
        self.fps_text = FpsText(self)
        self.enemy_info_text = EnemyInfoText(self)

    def _init_components(self):
        self.log.info('Initializing components')
        self.enemy_spawner = EnemySpawnMgr(self)
        self.mem_prof = MemProf()
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
        if self.mem_prof.snapshot:
            self.print_mem_snapshot()

    def do_one_frame(self):
        self.want_cpu_prof = False
        self.init_frame()
        self.handle_events()
        self.frame_inner_with_prof()
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

    def frame_inner_with_prof(self):
        if not self.want_cpu_prof:
            return self.do_frame_inner()
        self.log.info("Recording CPU profile")
        with CpuProfileContextManager('game_perf_3.prof'):
            self.do_frame_inner()
        self.log.info("CPU profile dumped to game_perf_3.prof")

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
        self.enemy_spawner.on_tick()

    def on_player_die(self):
        GameOver(self)
        self.log.info("Game over")

    # todo observer pattern for on_* methods
    def on_kill_enemy(self, enemy, bullet):
        self.enemy_spawner.on_kill_enemy(enemy)
        self.player.on_kill_enemy(enemy, bullet)

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                if DEBUG_MEMORY:
                    # don't print it here, want to do
                    # most processing after window closed
                    self.take_mem_snapshot()
                raise PGExit
            if event.type == pg.KEYDOWN and event.key == pg.K_p and DEBUG_CPU:
                self.want_cpu_prof = True
            if event.type == pg.KEYDOWN and event.key == pg.K_t and ALLOW_CHEATS:
                self.player.turrets += 20
                self.turrets_text.update()
            if event.type == pg.VIDEORESIZE:
                self.on_resize(event)

    def take_mem_snapshot(self):
        self.log.info("Taking memory snapshot")
        self.mem_prof.take_snapshot()
        self.log.info("Memory snapshot taken")

    def print_mem_snapshot(self):
        self.log.info("Processing and printing snapshot...")
        self.mem_prof.display_top()

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


class GameOver(TextSprite):
    def __init__(self, game: HasGame, text: str = None):
        self.set_game(game)
        if text is None:
            text = f'Game Over\nScore: {self.player.score}'
        super().__init__(None, text)

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
        strength = self.game.enemy_spawner.strength
        self.set_text(f'Score: {self.player.score}\n'
                      f'Enemies killed: {self.player.enemies_killed}\n'
                      f'Enemies currently alive: {len(self.game.enemies)}\n'
                      f'Enemy strength: {strength:>6.4f} pt/frame\n'
                      f'Enemy strength: {strength * 60:>6.3f} pt/sec')


class FpsText(TextSprite):
    def __init__(self, game: HasGame):
        super().__init__(game,  "FPS: N/A")

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
        self.game.enemy_spawner.enable(delay=40)
        self.game.initial_enemy.immobile = False
        self.log.info("Tutorial finished, entering main game.")


def main():
    print('Hello world')
    game = Game()
    game.init()
    game.mainloop()


if __name__ == '__main__':
    main()
