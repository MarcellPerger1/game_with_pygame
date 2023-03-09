import pygame
pg = pygame


# only job is to hold a rect as some methods require
# passing object with rect attribute not rect
class HasRect:
    def __init__(self, rect: pg.Rect):
        self.rect = rect


class HasImage:
    def __init__(self, image: pg.Surface):
        self.image = image


class HasRectImage(HasRect, HasImage):
    def __init__(self, rect: pg.Rect, image: pg.Surface):
        HasRect.__init__(self, rect)
        HasImage.__init__(self, image)
