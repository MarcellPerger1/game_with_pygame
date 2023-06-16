from __future__ import annotations

from typing import NoReturn, TYPE_CHECKING

import pygame as pg

from pg_util import rect_from_size
from uses_game import UsesGame
from util import option

if TYPE_CHECKING:
    from main import HasGame

Vec2 = pg.Vector2


class GamePgSprite(pg.sprite.Sprite, UsesGame):
    """Class inheriting from both `pygame.sprite.Sprite` and `UsesGame`"""
    def __init__(self, game: HasGame | None, *groups: pg.sprite.AbstractGroup):
        UsesGame.__init__(self, game)
        pg.sprite.Sprite.__init__(self, *groups)


class GroupMemberSprite(GamePgSprite):
    """Base class that only handles groups"""
    in_display: bool = None
    in_root: bool = True

    def __init__(self, game: HasGame | None, *groups: pg.sprite.AbstractGroup,
                 in_root: bool = None, in_display: bool = None):
        self.set_game(game, method_name='__init__')
        self._set_group_flags(in_root, in_display)
        super().__init__(None, *self._get_extra_groups(), *groups)

    def _set_group_flags(self, in_root: bool | None, in_display: bool | None):
        self.in_root = option(in_root, self.in_root)
        self.in_display = option(in_display, self.in_display)
        if self.in_display is None:
            # if not in root, probably should not be in display by default
            self.in_display = self.in_root

    def _get_extra_groups(self):
        extra = []
        if self.in_root:
            extra.append(self.root_group)
        if self.in_display:
            extra.append(self.display_group)
        return tuple(extra)


class DrawableSprite(GroupMemberSprite):
    # all abstract instances (but there's no way for making them actually abstract)
    rect: pg.Rect | None = None
    image: pg.Surface | None = None
    surf: pg.Surface | None = None

    def __init__(self, game: HasGame | None, *groups: pg.sprite.AbstractGroup,
                 surf: pg.Surface = None, rect: pg.Rect = None,
                 in_root: bool = None, in_display: bool = None):
        super().__init__(game, *groups, in_root=in_root, in_display=in_display)
        if surf is not None:
            self.set_surf(surf)
        if rect is not None:
            self.rect = rect

    def set_surf(self, surf: pg.Surface):
        self.surf = self.image = surf


class SizedSprite(DrawableSprite):
    size: Vec2 = None

    def __init__(self, game: HasGame | None, *groups: pg.sprite.AbstractGroup,
                 surf: pg.Surface = None, rect: pg.Rect = None, size: Vec2 = None,
                 in_root: bool = None, in_display: bool = None):
        super().__init__(game, *groups, surf=surf, rect=rect,
                         in_root=in_root, in_display=in_display)
        self.size = option(size, self.size)
        if self.size is None:
            raise self._err_missing_size("__init__")

    @classmethod
    def _err_missing_size(cls, method_name: str) -> TypeError:
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


class PositionedSprite(SizedSprite):
    pos: Vec2 = None

    def __init__(self, game: HasGame | None, *groups: pg.sprite.AbstractGroup,
                 surf: pg.Surface = None, rect: pg.Rect = None,
                 size: Vec2 = None, pos: Vec2 = None,
                 in_root: bool = None, in_display: bool = None):
        super().__init__(game, *groups, surf=surf, rect=rect, size=size,
                         in_root=in_root, in_display=in_display)
        self.pos = option(pos, self.pos)
        if self.pos is None:
            raise TypeError(f"pos must be passed to __init__"
                            " or set as a class attribute")


class SurfaceMakingSprite(PositionedSprite):
    def __init__(self, game: HasGame | None, *groups: pg.sprite.AbstractGroup,
                 surf: pg.Surface = None, rect: pg.Rect = None,
                 size: Vec2 = None, pos: Vec2 = None,
                 in_root: bool = None, in_display: bool = None):
        super().__init__(game, *groups, surf=surf, rect=rect, size=size,
                         pos=pos, in_root=in_root, in_display=in_display)
        if self.surf is None:
            self.surf = self.image = self.make_surface()

    def make_surface(self) -> pg.Surface:
        pass


class RectUpdatingSprite(SurfaceMakingSprite):
    _pos: Vec2 = None

    def __init__(self, game: HasGame | None, *groups: pg.sprite.AbstractGroup,
                 surf: pg.Surface = None, rect: pg.Rect = None,
                 size: Vec2 = None, pos: Vec2 = None,
                 in_root: bool = None, in_display: bool = None):
        super().__init__(game, *groups, surf=surf, rect=rect, size=size,
                         pos=pos, in_root=in_root, in_display=in_display)
        if self.rect is None:
            self.rect = self.create_rect()
            self.update_rect()

    def create_rect(self):
        return self.surf.get_rect()

    def update_rect(self):
        self.rect.center = self.pos

    @property
    def pos(self) -> Vec2:
        return self._pos

    @pos.setter
    def pos(self, value: Vec2):
        self.set_pos(value)

    def set_pos(self, value: Vec2):
        # IMPORTANT: need to use `_pos` to not cause
        # `pos.setter -> set_pos -> ...` recursion
        self._pos = value
        if self.rect is not None:
            # only call it after it's been initialized some way to prevent this from
            # being triggered by setting pos in `PositionedSprite`
            self.update_rect()


class CommonSprite(RectUpdatingSprite):
    """This is a base class for most sprites
    and needs to be subclassed to have any real use"""

    def __init__(self, game: HasGame | None, pos: Vec2, *groups: pg.sprite.AbstractGroup,
                 size=None, in_root: bool = None, in_display: bool = None,
                 surf: pg.surface.Surface = None, rect: pg.Rect = None):
        """Create this sprite

        Initialise this sprite with image and rect attributes

        :param game: The `Game` object
        :param pos: Center of sprite
        :param groups: The groups to add this to (display_group is automatically
            included unless specified otherwise, see not_in_root)
        :param size:  The size of this sprite; can also be on the class
        :param in_display: If False, doesn't add it to display_group
        :param surf: The surface to use, overrides `make_surface`
        """
        self.set_game(game, method_name='__init__')
        super().__init__(None, *groups, size=size, pos=pos,
                         in_root=in_root, in_display=in_display,
                         surf=surf, rect=rect)
        self.draw_sprite()

    def draw_sprite(self):
        """Called to draw the sprite into its local surface -
        this method could be used to load it from a texture for example.
        This should be overridden but isn't set as an abstractmethod for flexibility"""

    def make_surface(self):
        return pg.surface.Surface(self.size, pg.SRCALPHA)
