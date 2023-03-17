from __future__ import annotations

import cProfile
import random
import time
import tracemalloc
from typing import Any, NoReturn, Literal

import pygame

from util import option
from pg_util import rect_from_size, render_text, nearest_of_group
from containers import HasRect
from trigger_once import trigger_once
from mem_profile import MemProf


pg = pygame
Vec2 = pg.math.Vector2


DEBUG_MEMORY = False
DEBUG_CPU = True
USE_FLIP = True
SHOW_BULLETS = False  # todo test the effect of this on performance
SHOW_TURRET_RANGE = True

FPS = 60
SPEED = 3.8
P_RADIUS = 20
BULLET_SPEED = 25
TURRET_INTERVAL = 45
TURRET_RANGE = 140
ENEMY_SPEED = 2.3
SPAWN_INTERVAL_START = 65
SPAWN_ENEMY_DELAY_START = 75
MAX_ENEMIES_PER_TICK = 18
MIN_SPAWN_INTERVAL = 0.01


class PGExit(BaseException):
    pass


# noinspection PyShadowingNames
class UsesGame:
    game: Game

    def __init__(self, game: Game | UsesGame):
        if isinstance(game, UsesGame):
            game = game.game
        self.game = game


class CommonSprite(pg.sprite.Sprite):
    """This is a base class for most sprites
    and needs to be subclassed to have any real use"""
    size: Vec2 = None
    in_root = True

    def __init__(self, pos: Vec2, *groups: pg.sprite.AbstractGroup,
                 size=None, in_root: bool = None, surf: pg.surface.Surface = None):
        """Create this sprite

        Initialise this sprite with image and rect attributes

        :param pos: Center of sprite
        :param groups: The groups to add this to (root_group is automatically
            included unless specified otherwise, see not_in_root)
        :param size:  The size of this sprite; can also be on the class
        :param not_in_root: If True, doesn't add it to root_group
        """
        self.in_root = option(in_root, self.in_root)
        self.pos = pos
        self.size = option(size, self.size)
        groups = (game.root_group, *groups) if self.in_root else groups
        pg.sprite.Sprite.__init__(self, *groups)
        if self.size is None:
            raise self._err_missing_size("__init__")
        if surf is None:
            surf = self.make_surface()
        self.image = self.surf = surf
        self.rect = self.surf.get_rect(center=self.pos)
        self.draw_sprite()

    def draw_sprite(self):
        """Called to draw the sprite into its local surface -
        this method could be used to load it from a texture for example.
        This should be overridden but isn't set as an abstractmethod for flexibility"""

    def make_surface(self):
        return pg.surface.Surface(self.size, pg.SRCALPHA)

    def set_pos(self, value: Vec2):
        self.pos = self.rect.center = value

    @classmethod
    def _err_missing_size(cls, method_name: str) -> NoReturn:
        return TypeError(f"size must be passed to {method_name}"
                         " or set as a class attribute")

    @classmethod
    def get_virtual_rect(cls, pos: Vec2, size: Vec2 = None):
        if size is None:
            size = cls.size
        if size is None:
            raise cls._err_missing_size("get_virtual_rect")
        r = rect_from_size(size, center=pos)
        return r


class PerfMgr:
    mem_snapshot: tracemalloc.Snapshot | None = None
    curr_cpu_profile: cProfile.Profile | None = None

    def __init__(self, memory=DEBUG_MEMORY, cpu=DEBUG_CPU):
        self.do_memory = memory
        self.do_cpu = cpu
        self.mem_prof = MemProf(self.do_memory)

    def take_snapshot(self):
        self.mem_snapshot = self.mem_prof.take_snapshot()

    def print_snapshot(self, *args, **kwargs):
        self.mem_prof.display_top(self.mem_snapshot, *args, **kwargs)


class EnemySpawnMgr(UsesGame):
    def __init__(self, game_: Game):
        super().__init__(game_)
        self.is_enabled = False
        self.next_enemy_time: int | None = None
        self.enemy_spawn_interval: float = SPAWN_INTERVAL_START

    def handle_enemy_spawns(self):
        if not self.is_enabled:
            return
        if self.next_enemy_time is None:
            self.next_enemy_time = self.game.curr_tick + SPAWN_ENEMY_DELAY_START
        self.spawn_enemies()

    def spawn_enemies(self):
        enemies_this_tick = 0
        while (self.next_enemy_time <= self.game.curr_tick
               and enemies_this_tick < MAX_ENEMIES_PER_TICK):
            self.spawn_enemy()
            self.next_enemy_time += self.enemy_spawn_interval
            enemies_this_tick += 1
        # if it would've spawned an extra enemy, set the next enemy time to the current time
        # (won't spawn it this frame but still allows spawning a lot next frame)
        # should really be `ticks + epsilon` as next enemy should spawn at the very start
        # of the next frame but we aren't spawning extra enemies this frame anyway.
        if self.next_enemy_time < self.game.curr_tick:
            self.next_enemy_time = self.game.curr_tick

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

    # might use interval to determine health, etc.
    # noinspection PyMethodMayBeStatic
    def spawn_enemy(self):
        angle = random.uniform(0, 360)
        distance = random.uniform(250, 500)
        at = Vec2()
        at.from_polar((distance, angle))
        at += Vec2(self.game.player.pos)
        Enemy(at)


class Fonts:
    huge: pygame.font.Font
    monospace: pygame.font.Font

    @classmethod
    def init(cls):
        cls.huge = pygame.font.SysFont('Helvetica', 200, bold=True)
        cls.monospace = pygame.font.SysFont('monospace', 18)


# noinspection PyMethodMayBeStatic
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
        self._init_pygame()
        self._init_timing()
        self._init_fonts()
        self._init_groups()
        self._init_window()
        self._init_components()
        self._init_objects()

    def _init_pygame(self):
        print('[INFO] Initializing modules')
        n_pass, n_fail = pygame.init()
        print(f'[INFO] Initialized modules: {n_pass} successes, {n_fail} fails')

    def _init_fonts(self):
        print('[INFO] Initializing fonts')
        t0 = time.perf_counter()
        self.fonts = Fonts()
        self.fonts.init()
        t1 = time.perf_counter()
        print(f'[INFO] Initialized fonts in {t1 - t0:.2f}s')

    def _init_timing(self):
        print('[INFO] Initializing clock')
        self.curr_tick = 0
        self.clock = pg.time.Clock()

    def _init_groups(self):
        print('[INFO] Initializing groups')
        # todo should use LayeredUpdates / LayeredDirty
        self.root_group = pg.sprite.RenderUpdates()
        self.enemies = pg.sprite.Group()
        self.turret_range_overlays = pg.sprite.Group()
        self.bullets = pg.sprite.Group()
        self.turrets = pg.sprite.Group()

    def _init_window(self):
        print('[INFO] Initializing window')
        self.screen = pygame.display.set_mode((1600, 900), pg.RESIZABLE, display=0)
        self.dirty_this_frame: list[pg.Rect] = []
        self._clear_window()

    def _clear_window(self):
        print('[INFO] Clearing window')
        self.screen.fill((255, 255, 255))
        pg.display.flip()

    def _init_objects(self):
        print('[INFO] Initializing objects')
        self.player = Player(Vec2(700, 400))
        TurretItem(Vec2(400, 600))
        self.initial_enemy = Enemy(Vec2(50, 655), immobile=True)
        self.turrets_text = InvText("Turrets: 0")
        self.fps_text = FpsText("FPS: N/A")

    def _init_components(self):
        print('[INFO] Initializing components')
        self.enemy_spawner = EnemySpawnMgr(self)
        self.perf_mgr = PerfMgr()

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
        pygame.quit()
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
            print(f'Update took: {self.frame_time * 1000:.2f}ms')
            print(f'FPS: {self.clock.get_fps():.2f}')

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
            self.root_group.draw(self.screen)
            draw_turret_overlays()
            pg.display.flip()
        else:
            dirty = self.root_group.draw(self.screen)
            draw_turret_overlays()
            dirty += self.dirty_this_frame
            pg.display.update(dirty)

    def do_tick(self):
        if self.player.is_dead:
            return
        self.root_group.update()
        if not SHOW_BULLETS:
            # not in root_group so need to send update in own group
            self.bullets.update()
        on_post_tick()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if DEBUG_MEMORY:
                    self.perf_mgr.take_snapshot()
                raise PGExit
            if event.type == pg.KEYDOWN and event.key == pg.K_p:
                if DEBUG_CPU:
                    self.perf_mgr.curr_cpu_profile = cProfile.Profile()

    @property
    def ticks(self):
        return self.curr_tick

    @ticks.setter
    def ticks(self, value: int):
        self.curr_tick = value


if __name__ == '__main__':
    print('Hello world')


    class EveryNTicks:
        def __init__(self, n: int, offset=1):
            self.n = n
            self.started_at = game.curr_tick + offset

        def is_this_frame(self):
            return (game.curr_tick >= self.started_at
                    and (game.curr_tick - self.started_at) % self.n == 0)


    class Player(CommonSprite):
        size = Vec2(P_RADIUS * 2, P_RADIUS * 2)

        def __init__(self, pos: Vec2):
            super().__init__(pos)
            self.turrets = 0
            self.is_dead = False
            self.enemies_killed = 0
            self.turret_parts = 0.0

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
            if self.turrets > 0:
                mouse_pos = Vec2(pg.mouse.get_pos())
                if not pg.sprite.spritecollide(
                        HasRect(Turret.get_virtual_rect(mouse_pos)), game.turrets, False):
                    Turret(mouse_pos)
                    self.turrets -= 1
                    update_turrets_text()

        def on_kill_enemy(self, _enemy: Enemy, _bullet: Bullet):
            self.enemies_killed += 1
            self.turret_parts += 0.2
            if self.turret_parts >= 1.0:
                extra_turrets, self.turret_parts = divmod(self.turret_parts, 1)
                self.turrets += round(extra_turrets)  # not int() coz fp precision
                update_turrets_text()


    class Collectable(CommonSprite):
        size = Vec2(12, 12)  # 'standard' size for a collectable; override this

        def __init__(self, pos: Vec2):
            super().__init__(pos)

        # noinspection PyMethodMayBeStatic
        def on_collect(self):
            """This method is called when this has been collected (after being kill-ed)"""

        def update(self, *args: Any, **kwargs: Any) -> None:
            if pg.sprite.collide_rect(self, game.player):
                self.kill()
                self.on_collect()

    class TurretItem(Collectable):
        def draw_sprite(self):
            pg.draw.rect(self.surf, 'darkolivegreen3', self.surf.get_rect())

        def on_collect(self):
            game.player.turrets += 1
            update_turrets_text()


    class Turret(CommonSprite):
        size = Vec2(20, 20)

        def __init__(self, pos: Vec2, *groups: pg.sprite.AbstractGroup,
                     interval: int = TURRET_INTERVAL):
            super().__init__(pos, game.turrets, *groups)
            self.interval = interval
            self.shot_on_tick = None
            if SHOW_TURRET_RANGE:
                TurretRangeIndicator(self.pos)
            Tutorial.place_turret()

        def draw_sprite(self):
            pg.draw.rect(self.surf, 'darkgreen', self.surf.get_rect())

        def can_shoot(self):
            return (self.shot_on_tick is None
                    or game.curr_tick >= self.shot_on_tick + self.interval)

        def update(self, *args: Any, **kwargs: Any) -> None:
            if self.can_shoot():
                target: Enemy = nearest_of_group(self.pos, game.enemies)
                if target is not None and self.can_shoot_enemy(target):
                    Bullet(self.pos, target.pos)
                    self.shot_on_tick = game.curr_tick

        def can_shoot_enemy(self, enemy: Enemy):
            return self.pos.distance_squared_to(enemy.pos) <= TURRET_RANGE * TURRET_RANGE

    class TurretRangeIndicator(CommonSprite):
        size = Vec2(TURRET_RANGE * 2, TURRET_RANGE * 2)
        common_surf: pg.surface.Surface = None
        """The surface that is drawn for each overlay"""

        need_redraw: list[TurretRangeIndicator] | Literal['all'] = 'all'
        overlays_surf: pg.Surface = None

        def __init__(self, pos: Vec2, *groups: pg.sprite.AbstractGroup):
            super().__init__(pos, game.turret_range_overlays, *groups, in_root=False)
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
            game.dirty_this_frame.append(self.rect)
            self.request_redraw(self)

        @classmethod
        def request_redraw(cls, *args: TurretRangeIndicator):
            if cls.need_redraw == 'all':
                return
            cls.need_redraw += args

        @classmethod
        def make_overlay_surf(cls, remake_force=False):
            if cls.overlays_surf is None or remake_force:
                cls.overlays_surf = pg.Surface(game.screen.get_size(), pg.SRCALPHA)

        @classmethod
        def draw_all(cls):
            if not cls.need_redraw or not SHOW_TURRET_RANGE:
                return
            cls.make_overlay_surf()
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
        def blit_all(cls):
            return game.screen.blit(cls.overlays_surf, game.screen.get_rect())


    class Bullet(CommonSprite):
        size = Vec2(6, 6)

        def __init__(self, pos: Vec2, target: Vec2, *groups: pg.sprite.AbstractGroup):
            super().__init__(pos, game.bullets, *groups, in_root=SHOW_BULLETS)
            self.target = target

        def draw_sprite(self):
            if SHOW_BULLETS:
                pg.draw.rect(self.surf, 'red4', self.surf.get_rect())
            else:
                # use less memory, as it can now free self.surf
                # (set in CommonSprite.__init__)
                self.surf = None

        def on_hit_enemy(self, enemy: CommonEnemy):
            enemy.on_hit_by_bullet(self)
            self.kill()

        def update(self, *args: Any, **kwargs: Any) -> None:
            enemies_hit = pg.sprite.spritecollide(self, game.enemies, False)
            if len(enemies_hit) != 0:
                # only hit first one
                enemy: CommonEnemy = enemies_hit[0]
                self.on_hit_enemy(enemy)
                return
            if self.pos == self.target:
                self.kill()
            self.pos = self.pos.move_towards(self.target, BULLET_SPEED)
            self.rect.center = self.pos


    class CommonEnemy(CommonSprite):
        def __init__(self, pos: Vec2,
                     *groups: pg.sprite.AbstractGroup,
                     is_in_enemies=True, **kwargs):
            groups = (*groups, game.enemies) if is_in_enemies else groups
            super(CommonEnemy, self).__init__(pos, *groups, **kwargs)

        def on_hit_by_bullet(self, bullet: Bullet):
            self.kill()
            on_kill_enemy(self, bullet)

        # noinspection PyMethodMayBeStatic
        def on_collide_player(self):
            game.player.is_dead = True
            GameOver(f'Game Over\nScore: {game.player.enemies_killed}')
            print('You died')

        def update(self, *args: Any, **kwargs: Any) -> None:
            """This update function handles killing player on contact"""
            if pg.sprite.collide_rect(self, game.player):
                self.on_collide_player()

    class Enemy(CommonEnemy):
        size = Vec2(30, 30)

        def __init__(self, pos: Vec2, immobile=False):
            super().__init__(pos)
            self.immobile = immobile

        def draw_sprite(self):
            pg.draw.rect(self.surf, 'red', self.surf.get_rect())

        def update(self, *args: Any, **kwargs: Any) -> None:
            super().update(*args, **kwargs)
            if not self.immobile:
                self.pos = self.pos.move_towards(game.player.pos, ENEMY_SPEED)
                self.rect.center = self.pos

    class EnemyWithHealth(CommonEnemy):
        size = Vec2(30, 30)

        def __init__(self, pos: Vec2, health: float, immobile=False):
            super().__init__(pos)
            self.health = health
            self.immobile = immobile


    class GameOver(pygame.sprite.Sprite):
        def __init__(self, text: str):
            super().__init__(game.root_group)
            self.text = text
            self.pos = game.screen.get_rect().center
            self.surf = self.image = render_text(
                game.fonts.huge, self.text, color='black', justify='center')
            self.rect = self.surf.get_rect(center=self.pos)

    class InvText(pygame.sprite.Sprite):
        text: str
        surf: pg.surface.Surface
        image: pg.surface.Surface
        rect: pg.Rect

        def __init__(self, text: str):
            super().__init__(game.root_group)
            self.topleft = Vec2(5, 5)
            self.set_text(text)

        def set_text(self, text: str):
            self.text = text
            self.surf = self.image = game.fonts.monospace.render(
                self.text, True, pg.color.Color('black'))
            self.rect = self.surf.get_rect(topleft=self.topleft)

    class FpsText(pg.sprite.Sprite):
        text: str
        surf: pg.surface.Surface
        image: pg.surface.Surface
        rect: pg.Rect

        def __init__(self, text: str):
            super().__init__(game.root_group)
            self.topright = Vec2(game.screen.get_width() - 5, 5)
            self.set_text(text)

        def set_text(self, text: str):
            self.text = text
            self.surf = self.image = game.fonts.monospace.render(
                self.text, True, pg.color.Color('black'))
            self.rect = self.surf.get_rect(topright=self.topright)

        def update(self, *args: Any, **kwargs: Any) -> None:
            if game.curr_tick % 5 == 1:
                self.set_text(f'FPS: {game.clock.get_fps():.2f}')


    def on_post_tick():
        game.enemy_spawner.handle_enemy_spawns()

    class Tutorial:
        @classmethod
        @trigger_once
        def place_turret(cls):
            game.enemy_spawner.is_enabled = True
            game.initial_enemy.immobile = False


    def update_turrets_text():
        game.turrets_text.set_text(f'Turrets: {game.player.turrets}')


    def draw_turret_overlays():
        TurretRangeIndicator.draw_all()
        return TurretRangeIndicator.blit_all()


    def on_kill_enemy(enemy, bullet):
        game.enemy_spawner.increment_interval_once()
        game.player.on_kill_enemy(enemy, bullet)


    game = Game()
    game.init()
    game.mainloop()
