from __future__ import annotations

from typing import TypeVar, Any
from unittest import TestCase

from sprite_bases import GroupMemberSprite

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


class TestGroupMemberSprite(TestCase):
    def inst(self, klass=GroupMemberSprite):
        return new(klass)

    def test__set_group_flags(self):
        class NoPropsSub(GroupMemberSprite):
            display_group = None
            root_group = None

        def setup_inst(root, display):
            # noinspection PyTypeChecker
            s2: NoPropsSub = self.inst(NoPropsSub)
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


