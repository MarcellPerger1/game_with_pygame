from __future__ import annotations

import contextlib
from typing import TypeVar, Any, Iterable
from unittest import TestCase
from unittest.mock import patch

import pygame as pg

from sprite_bases import GroupMemberSprite, DrawableSprite
from uses_game import UsesGame

T = TypeVar('T')


def new(t: type[T]) -> T:
    return t.__new__(t)


class _NamedObject(object):
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"<_NamedObject: {self.name}>"


def obj(name: str = None) -> Any:
    if not name:
        return object()
    else:
        return _NamedObject(name)


class NoPropsGroupMember(GroupMemberSprite):
    display_group = None
    root_group = None


class TestGroupMemberSprite(TestCase):
    def inst(self, klass=GroupMemberSprite):
        return new(klass)

    def test__set_group_flags(self):
        def setup_inst(root, display):
            # noinspection PyTypeChecker
            s2: NoPropsGroupMember = self.inst(NoPropsGroupMember)
            s2.root_group = obj("root_group")
            s2.display_group = obj("display_group")
            s2.in_root = root
            s2.in_display = display
            return s2

        s = setup_inst(False, False)
        self.assertEqual(s._get_extra_groups(), ())
        s = setup_inst(False, True)
        self.assertEqual(s._get_extra_groups(), (s.display_group,))
        s = setup_inst(True, False)
        self.assertEqual(s._get_extra_groups(), (s.root_group,))
        s = setup_inst(True, True)
        # order doesn't matter
        self.assertEqual(set(s._get_extra_groups()),
                         {s.display_group, s.root_group})

    def test__get_extra_groups(self):
        for in_root in True, False:
            for in_display in True, False:
                with self.subTest(in_root=in_root, in_display=in_display):
                    s = self.inst()
                    s._set_group_flags(in_root, in_display)
                    self.assertEqual(s.in_root, in_root)
                    self.assertEqual(s.in_display, in_display)
        with self.subTest(in_root=None, in_display=None):
            s = self.inst()
            s._set_group_flags(None, None)
            self.assertEqual(s.in_root, True)
            self.assertEqual(s.in_display, True)
        for in_root in True, False:
            with self.subTest(in_root=in_root, in_display=None):
                s = self.inst()
                s._set_group_flags(in_root, None)
                self.assertEqual(s.in_root, in_root)
                self.assertEqual(s.in_display, in_root)
        v1 = obj()
        v2 = obj()

        class Sub(GroupMemberSprite):
            in_root = v1
            in_display = v2
        s = self.inst(Sub)
        s._set_group_flags(None, None)
        self.assertIs(s.in_root, v1)
        self.assertIs(s.in_display, v2)

    def test_init_GroupMemberSprite(self):
        def setup_inst():
            # noinspection PyTypeChecker
            s2: NoPropsGroupMember = self.inst(NoPropsGroupMember)
            s2.root_group = pg.sprite.Group()
            s2.display_group = pg.sprite.Group()
            return s2

        game = obj()
        g1 = pg.sprite.Group()
        g2 = pg.sprite.Group()
        inst = setup_inst()
        inst.__init__(game, g1, g2, in_display=False)
        self.assertIs(inst.game, game)
        self.assertEqual(set(inst.groups()), {g1, g2, inst.root_group})
        self.assertEqual(inst.in_root, True)
        self.assertEqual(inst.in_display, False)
        i2 = setup_inst()
        i2.__init__(game, in_root=False)
        self.assertEqual(i2.game, game)
        self.assertEqual(set(i2.groups()), set())
        self.assertEqual(i2.in_root, False)
        self.assertEqual(i2.in_display, False)


class TestDrawableSprite(TestGroupMemberSprite):
    def test_set_surf(self):
        inst = new(DrawableSprite)
        surf = obj("surf")
        inst.set_surf(surf)
        self.assertIs(inst.image, surf)
        self.assertIs(inst.surf, surf)

    def test_init_DrawableSprite(self):
        surf = obj("surf")
        rect = obj("rect")
        with MultiContextManager(patch_groups(DrawableSprite)):
            inst = DrawableSprite(obj(), surf=surf, rect=rect)
            self.assertIs(inst.surf, surf)
            self.assertIs(inst.image, surf)
            self.assertIs(inst.rect, rect)

        inst: DrawableSprite = NoPropsDrawableSprite.new_with_dummy_groups()
        inst.rect = rect
        inst.image = inst.surf = surf
        inst.__init__(obj())
        self.assertIs(inst.surf, surf)
        self.assertIs(inst.image, surf)
        self.assertIs(inst.rect, rect)


class NoGroupPropsMixin:
    display_group = None
    root_group = None

    def __init__(self, *args, **kwargs):
        # next class in mro NOT superclass
        super().__init__(*args, **kwargs)

    @classmethod
    def new_with_dummy_groups(cls) -> Any | NoGroupPropsMixin:
        assert (
            UsesGame not in cls.mro()
            or cls.mro().index(cls) < cls.mro().index(UsesGame)
        ), "NoGroupPropsMixin must come before UsesGame in mro"
        inst = cls.__new__(cls)
        inst.root_group = pg.sprite.Group()
        inst.display_group = pg.sprite.Group()
        return inst


class NoPropsDrawableSprite(NoGroupPropsMixin, DrawableSprite):
    ...


class MultiContextManager(contextlib.AbstractContextManager):
    def __init__(self, *contexts: contextlib.AbstractContextManager):
        self.contexts = contexts

    def __enter__(self):
        return tuple(c.__enter__() for c in self.contexts)

    def __exit__(self, exc_type, exc_val, exc_tb):
        # exit out of the contexts backwards:
        # enter 0 -> (enter 1 -> (...) -> exit 1) -> exit 0
        ignore_error = False
        for c in reversed(self.contexts):
            if c.__exit__(exc_type, exc_val, exc_tb):
                ignore_error = True
                # don't propagate error to outer context
                # (this context caught the error)
                exc_type = exc_val = exc_tb = None
        return ignore_error


def multipatch(t: type | object, *patches: tuple[str, Any], **kw_patches):
    return MultiContextManager(
        *(patch.object(t, k, v) for k, v in patches),
        *(patch.object(t, k, v) for k, v in kw_patches.items())
    )


def patch_groups(t: type):
    return MultiContextManager(
        patch.object(t, 'root_group', pg.sprite.Group()),
        patch.object(t, 'display_group', pg.sprite.Group())
    )
