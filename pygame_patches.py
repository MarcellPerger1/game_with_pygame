from __future__ import annotations

import ctypes
import sys
from typing import Sequence

import pygame

pg = pygame
Vec2 = pg.Vector2


unsafe_PyDecref = ctypes.pythonapi.Py_DecRef
unsafe_PyDecref.argtypes = [ctypes.py_object]
unsafe_PyDecref.restype = None


def pg_has_memory_leak():
    c = (4, 5)  # need to use a tuple
    pos = Vec2(12, 13)
    did_leak = False
    orig_refcount = sys.getrefcount(c)
    try:
        pos.distance_squared_to(c)
    finally:
        if sys.getrefcount(c) > orig_refcount:
            did_leak = True
            # leaked a reference in distance_squared_to, need to clean it up now
            unsafe_PyDecref(c)
    return did_leak

if pg_has_memory_leak():
    print('[INFO] This version of pygame has a memory leak'
          ' but we have fixed this from the python code, see issue #3532', file=sys.stderr)
    def dist_squared_to(a: Vec2 | Sequence[float], b: Vec2 | Sequence[float]):
        # convert to vectors as issue doesn't happen with vectors
        return Vec2(a).distance_squared_to(Vec2(b))
else:
    def dist_squared_to(a: Vec2 | Sequence[float], b: Vec2 | Sequence[float]):
        # this also accepts a Vector-like obj for `a`
        return Vec2(a).distance_squared_to(b)
