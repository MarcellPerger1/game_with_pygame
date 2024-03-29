from __future__ import annotations

import contextlib
from typing import TypeVar, Any, Callable
from unittest import TestCase
from unittest.mock import patch, PropertyMock, NonCallableMock

import pygame as pg
from pygame import Vector2 as Vec2

from sprite_bases import (GroupMemberSprite, DrawableSprite, SizedSprite,
                          PositionedSprite, SurfaceMakingSprite,
                          RectUpdatingSprite)
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


class BaseTest(TestCase):
    _pre_init_list: tuple[tuple[BaseTest, Callable[[BaseTest, Any], Any]]] = ()
    """``((type, pre_init_fn), ...)``"""
    target_cls = None

    def on_pre_init(self, inst):
        ...

    def pre_init(self, inst, caller_cls):
        for cls, fn in self._pre_init_list:
            # only call the pre_init if this test doesn't belong to it.
            # If this pre_init belongs to this test,
            # we're testing the class with this pre_init so we may want to
            # set new values for the fields so don't do anything
            # as the new values would interfere with the test values
            # e.g. SizedSprite sets .size in pre_init but the tests
            # also require it to be set to their own value
            # so we need to skip running this pre_init
            if cls != caller_cls and cls.target_cls != caller_cls:
                fn(self, inst)

    def __init_subclass__(cls, **kwargs):
        if (cls.on_pre_init is not None
                and cls.on_pre_init != BaseTest.on_pre_init
                and not getattr(cls.on_pre_init, 'is_nop', False)
                and cls.on_pre_init != getattr(super(cls, cls), 'on_pre_init', None)):
            cls._pre_init_list += ((cls, cls.on_pre_init),)

    def new_inst(self, klass=None):
        if klass is None:
            klass = self.target_cls
        return new(klass)

    def init_inst_obj(self, inst, caller_cls, *args, **kwargs):
        self.pre_init(inst, caller_cls)
        inst.__init__(*args, **kwargs)

    def init_new(self, caller_cls, *args, **kwargs):
        inst = self.new_inst()
        self.init_inst_obj(inst, caller_cls, *args, **kwargs)


def mark_as_nop(fn):
    fn.is_nop = True


class TestGroupMemberSprite(BaseTest):
    target_cls = GroupMemberSprite

    @classmethod
    def no_props_cls(cls):
        class NoPropsSprite(cls.target_cls):
            display_group = None
            root_group = None

        return NoPropsSprite

    def test__set_group_flags(self):
        def setup_inst(root, display):
            s2 = self.new_inst(self.no_props_cls())
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
                    s = self.new_inst()
                    s._set_group_flags(in_root, in_display)
                    self.assertEqual(s.in_root, in_root)
                    self.assertEqual(s.in_display, in_display)
        with self.subTest(in_root=None, in_display=None):
            s = self.new_inst()
            s._set_group_flags(None, None)
            self.assertEqual(s.in_root, True)
            self.assertEqual(s.in_display, True)
        for in_root in True, False:
            with self.subTest(in_root=in_root, in_display=None):
                s = self.new_inst()
                s._set_group_flags(in_root, None)
                self.assertEqual(s.in_root, in_root)
                self.assertEqual(s.in_display, in_root)
        v1 = obj()
        v2 = obj()

        class Sub(self.target_cls):
            in_root = v1
            in_display = v2

        s = self.new_inst(Sub)
        s._set_group_flags(None, None)
        self.assertIs(s.in_root, v1)
        self.assertIs(s.in_display, v2)

    def test_init_GroupMemberSprite(self):
        def setup_inst():
            i = self.new_inst(self.no_props_cls())
            i.root_group = pg.sprite.Group()
            i.display_group = pg.sprite.Group()
            self.pre_init(i, TestGroupMemberSprite)
            return i

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
    target_cls = DrawableSprite

    @classmethod
    def no_props_mixed(cls):
        class NoPropsMixedSprite(NoGroupPropsMixin, cls.target_cls):
            ...

        return NoPropsMixedSprite

    def test_set_surf(self):
        inst = new(DrawableSprite)
        surf = obj("surf")
        inst.set_surf(surf)
        self.assertIs(inst.image, surf)
        self.assertIs(inst.surf, surf)

    def test_init_DrawableSprite(self):
        surf = obj("surf")
        rect = obj("rect")
        with MultiContextManager(patch_groups(self.target_cls)):
            inst = self.new_inst()
            self.pre_init(inst, DrawableSprite)
            inst.__init__(obj(), surf=surf, rect=rect)
            self.assertIs(inst.surf, surf)
            self.assertIs(inst.image, surf)
            self.assertIs(inst.rect, rect)

        inst: DrawableSprite = self.no_props_mixed().new_with_dummy_groups()
        inst.rect = rect
        inst.image = inst.surf = surf
        self.pre_init(inst, DrawableSprite)
        inst.__init__(obj())
        self.assertIs(inst.surf, surf)
        self.assertIs(inst.image, surf)
        self.assertIs(inst.rect, rect)


class TestSizedSprite(TestDrawableSprite):
    target_cls = SizedSprite

    def on_pre_init(self, inst: SizedSprite):
        inst.size = Vec2(40, 30)

    def test_get_virtual_rect(self):
        sz = Vec2(25, 20)
        sz2 = Vec2(-99, 61)
        pos = Vec2(40, 100)

        class Sub(self.target_cls):
            size = sz

        # dark magic with patch(...):
        # it LITERALLY replaces the rect_from_size
        # global in the sprite_bases module with a mock version!
        with patch('sprite_bases.rect_from_size') as m:
            m.return_value = obj("returned rect")
            self.assertIs(Sub.get_virtual_rect(pos), m.return_value)
            m.assert_called_once_with(sz, center=pos)

        with patch('sprite_bases.rect_from_size') as m:
            m.return_value = obj("returned rect")
            self.assertIs(self.target_cls.get_virtual_rect(pos, sz),
                          m.return_value)
            m.assert_called_once_with(sz, center=pos)

        with patch('sprite_bases.rect_from_size') as m:
            m.return_value = obj("returned rect")
            self.assertIs(Sub.get_virtual_rect(pos, Vec2(sz2)),
                          m.return_value)
            m.assert_called_once_with(sz2, center=pos)

        with self.assertRaises(TypeError):
            self.target_cls.get_virtual_rect(pos)

    def test_init_SizedSprite(self):
        size = obj("size")
        with MultiContextManager(patch_groups(self.target_cls)):
            inst = self.new_inst()
            self.pre_init(inst, SizedSprite)
            inst.__init__(obj(), size=size)
            self.assertIs(inst.size, size)

        inst = self.no_props_mixed().new_with_dummy_groups()
        inst.size = size
        self.pre_init(inst, SizedSprite)
        inst.__init__(obj())
        self.assertIs(inst.size, size)

        inst = self.no_props_mixed().new_with_dummy_groups()
        inst.size = obj("size_on_class")
        self.pre_init(inst, SizedSprite)
        inst.__init__(obj(), size=size)
        self.assertIs(inst.size, size)

        # if later the error behavior changes, this is the part to change
        with self.assertRaises(TypeError) as r:
            inst = self.no_props_mixed().new_with_dummy_groups()
            self.pre_init(inst, SizedSprite)
            inst.__init__(obj())
        self.assertIn('size', str(r.exception))


class TestPositionedSprite(TestSizedSprite):
    target_cls = PositionedSprite

    def test_init_PositionedSprite(self):
        pos = obj("pos")
        with MultiContextManager(patch_groups(self.target_cls)):
            inst = self.new_inst()
            self.pre_init(inst, PositionedSprite)
            inst.__init__(obj(), pos=pos)
            self.assertIs(inst.pos, pos)

        with MultiContextManager(
                patch_groups(self.target_cls),
                patch.object(self.target_cls, 'pos', pos)):
            inst = self.new_inst()
            self.pre_init(inst, PositionedSprite)
            inst.__init__(obj())
            self.assertIs(inst.pos, pos)

        with MultiContextManager(
                patch_groups(self.target_cls),
                patch.object(self.target_cls, 'pos', obj("pos on class"))):
            inst = self.new_inst()
            self.pre_init(inst, PositionedSprite)
            inst.__init__(obj(), pos=pos)
            self.assertIs(inst.pos, pos)

        with MultiContextManager(patch_groups(self.target_cls)):
            inst = self.new_inst()
            self.pre_init(inst, PositionedSprite)
            with self.assertRaises(TypeError) as r:
                inst.__init__(obj())
            self.assertIn('pos', str(r.exception))

    def on_pre_init(self, inst: PositionedSprite):
        inst.pos = Vec2(23, 109)


class TestSurfaceMakingSprite(TestPositionedSprite):
    target_cls = SurfaceMakingSprite

    def test_init_SurfaceMakingSprite(self):
        with patch_groups(self.target_cls), \
                patch.object(self.target_cls, 'make_surface') as m:
            inst: SurfaceMakingSprite = self.new_inst()
            self.pre_init(inst, SurfaceMakingSprite)
            m.return_value = obj('make_surface return')
            inst.__init__(obj())
            m.assert_called_once_with()
            self.assertIs(inst.surf, m.return_value)
            self.assertIs(inst.image, m.return_value)


class TestRectUpdatingSprite(TestSurfaceMakingSprite):
    target_cls = RectUpdatingSprite

    def on_pre_init(self, inst: RectUpdatingSprite):
        inst.create_rect = lambda: inst.rect
        inst.update_rect = lambda: None

    def test_init_RectUpdatingSprite(self):
        # if rect provided
        # the set_pos mock is so that we don't count the call from there
        def new_set_pos(self_inner, value):
            self_inner._pos = value

        with patch.object(self.target_cls, 'update_rect') as m_update_rect, \
                patch.object(self.target_cls, 'create_rect') as m_create_rect, \
                patch.object(self.target_cls, 'set_pos', new_set_pos), \
                patch_groups(self.target_cls):
            inst: RectUpdatingSprite = self.new_inst()
            self.pre_init(inst, RectUpdatingSprite)
            rect = inst.rect = obj("rect")
            inst.__init__(obj("game"))
            self.assertIs(inst.rect, rect)
            m_update_rect.assert_not_called()
            m_create_rect.assert_not_called()
        # if rect not provided
        with patch.object(self.target_cls, 'update_rect') as m_update_rect, \
                patch.object(self.target_cls, 'create_rect') as m_create_rect, \
                patch_groups(self.target_cls):
            rect = m_create_rect.return_value = obj("rect")

            def remember_pos_value(*_, **__):
                nonlocal rect_in_update_fn
                rect_in_update_fn = inst.rect

            rect_in_update_fn = None
            m_update_rect.side_effect = remember_pos_value

            inst: RectUpdatingSprite = self.new_inst()
            self.pre_init(inst, RectUpdatingSprite)
            inst.__init__(obj("game"))
            self.assertIs(inst.rect, rect)
            m_create_rect.assert_called_once_with()
            m_update_rect.assert_called_once_with()
            self.assertIs(rect_in_update_fn, rect)

    def test_create_rect(self):
        inst = self.new_inst()
        inst.surf = inst.image = pg.Surface((23, 31))
        self.assertEqual(inst.create_rect(), pg.Rect(0, 0, 23, 31))

    def test_update_rect(self):
        inst: RectUpdatingSprite = self.new_inst()
        inst.pos = obj("pos")
        rect_mock = inst.rect = NonCallableMock()
        mock_center = type(rect_mock).center = PropertyMock()
        inst.update_rect()
        mock_center.assert_called_once_with(inst.pos)

    def test_pos_getter(self):
        inst: RectUpdatingSprite = self.new_inst()
        pos = inst._pos = obj("pos")
        self.assertIs(inst.pos, pos)

    def test_pos_setter(self):
        with patch.object(self.target_cls, 'set_pos') as m:
            inst: RectUpdatingSprite = self.new_inst()
            pos = inst.pos = obj("pos")
            m.assert_called_once_with(pos)

    def test_set_pos(self):
        pos = obj("pos")
        with patch.object(self.target_cls, 'update_rect') as m:
            inst: RectUpdatingSprite = self.new_inst()
            inst.rect = None
            inst.set_pos(pos)
            self.assertIs(inst._pos, pos)
            m.assert_not_called()
        with patch.object(self.target_cls, 'update_rect') as m:
            def remember_pos_value(*_, **__):
                nonlocal pos_in_update_fn
                pos_in_update_fn = inst._pos

            pos_in_update_fn = None
            m.side_effect = remember_pos_value

            inst: RectUpdatingSprite = self.new_inst()
            inst.rect = obj("rect")
            inst.set_pos(pos)
            self.assertIs(inst._pos, pos)
            m.assert_called_once_with()
            self.assertIs(pos_in_update_fn, pos)


class NoGroupPropsMixin:
    display_group = None
    root_group = None

    def __init__(self, *args, **kwargs):
        # next class in mro NOT superclass
        super().__init__(*args, **kwargs)

    @classmethod
    def new_with_dummy_groups(cls) -> Any | NoGroupPropsMixin:
        assert (UsesGame not in cls.mro()
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
