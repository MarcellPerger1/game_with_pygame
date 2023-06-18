from typing import Any
from unittest import TestCase
from unittest.mock import patch

from uses_game import UsesGame


def obj() -> Any:
    return object()


class TestUsesGame(TestCase):
    def test__set_game__game(self):
        inst = UsesGame.__new__(UsesGame)
        g = obj()
        inst.set_game(g)
        self.assertIs(inst.game, g)

    def test__set_game__uses_game(self):
        inst = UsesGame.__new__(UsesGame)
        g = obj()
        ug = UsesGame.__new__(UsesGame)
        ug.game = g
        inst.set_game(g)
        self.assertIs(inst.game, g)

    def test__set_game__error_game(self):
        inst = UsesGame.__new__(UsesGame)
        with self.assertRaises(RuntimeError):
            inst.set_game(None)

    def test__set_game__error_uses_game(self):
        inst = UsesGame.__new__(UsesGame)
        ug = UsesGame.__new__(UsesGame)
        ug.game = None
        with self.assertRaises(RuntimeError):
            inst.set_game(ug)

    def test__set_game__not_strict_game(self):
        inst = UsesGame.__new__(UsesGame)
        inst.set_game(None, False)
        self.assertIsNone(inst.game)

    def test__set_game__not_strict_uses_game(self):
        inst = UsesGame.__new__(UsesGame)
        ug = UsesGame.__new__(UsesGame)
        ug.game = None
        inst.set_game(ug, False)
        self.assertIsNone(inst.game)

    def test__set_game__from_class(self):
        g = obj()

        class Sub(UsesGame):
            game = g
        inst = Sub.__new__(Sub)
        inst.set_game(None)
        self.assertIs(inst.game, g)

    def test__set_game__new_has_prio(self):
        inst = UsesGame.__new__(UsesGame)
        inst.game = obj()
        g2 = obj()
        inst.set_game(g2)
        self.assertIs(inst.game, g2)

    def test__init__game(self):
        g = obj()
        inst = UsesGame(g)
        self.assertIs(inst.game, g)

    def test__init__uses_game(self):
        g = obj()
        ug = UsesGame.__new__(UsesGame)
        ug.game = g
        inst = UsesGame(ug)
        self.assertIs(inst.game, g)

    def test__init__calls_set_game(self):
        with patch.object(UsesGame, 'set_game') as mock_set_game:
            g = obj()
            UsesGame(g)
            mock_set_game.assert_called_once_with(g, True, '__init__')

