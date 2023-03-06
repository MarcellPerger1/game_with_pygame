from __future__ import annotations

import pygame as pg
from pygame import Vector2 as Vec2


def rect_from_size(sz: Vec2, **kwargs):
    rect = pg.Rect((0, 0), sz)
    for k, v in kwargs.items():
        setattr(rect, k, v)
    return rect


def justify_rect(rect: pg.Rect, justify: str, tot_width: int | float):
    justify = justify.lower()
    rect = rect.copy()
    if justify == 'left':
        pass  # already at the left
    elif justify in 'center':
        rect.centerx = tot_width / 2
    elif justify == 'right':
        rect.right = tot_width
    return rect


def render_text(font: pg.font.Font, text: str, antialias=True, color='black', bg=None,
                justify='left'):
    lines = text.splitlines()
    rendered_lines = [font.render(line, antialias, color, bg) for line in lines]
    tot_height = sum(r.get_height() for r in rendered_lines)
    tot_width = max(r.get_width() for r in rendered_lines)
    dest = pg.surface.Surface((tot_width, tot_height), pg.SRCALPHA)
    y0 = 0
    for src in rendered_lines:
        w, h = src.get_size()
        dest_rect = justify_rect(pg.Rect((0, y0), (w, h)), justify, tot_width)
        dest.blit(src, dest_rect)
        y0 += h
    return dest
