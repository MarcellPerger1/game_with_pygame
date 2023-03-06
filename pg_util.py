import pygame as pg
from pygame import Vector2 as Vec2


def rect_from_size(sz: Vec2, **kwargs):
    rect = pg.Rect((0, 0), sz)
    for k, v in kwargs.items():
        setattr(rect, k, v)
    return rect
