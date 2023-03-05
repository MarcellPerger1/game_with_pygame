from typing import Any

import pygame
pg = pygame
Vec2 = pg.math.Vector2


FPS = 60
SPEED = 3.8
P_RADIUS = 10


class PGExit(BaseException):
    pass


clock = pg.time.Clock()


def main():
    class Player(pg.sprite.Sprite):
        def __init__(self):
            super().__init__(root_group)
            self.pos = Vec2(200, 100)
            self.size = Vec2(P_RADIUS * 2, P_RADIUS * 2)
            self.image = self.surf = pg.surface.Surface(self.size, pg.SRCALPHA)
            pg.draw.circle(self.surf, 'blue', self.size/2, P_RADIUS, 1)
            self.rect = self.surf.get_rect(center=self.pos)

        def update(self, *args: Any, **kwargs: Any) -> None:
            pressed = pg.key.get_pressed()
            m = Vec2()
            if pressed[pg.K_DOWN] or pressed[pg.K_s]:
                m += Vec2(0, 1)
            if pressed[pg.K_UP] or pressed[pg.K_w]:
                m += Vec2(0, -1)
            if pressed[pg.K_LEFT] or pressed[pg.K_a]:
                m += Vec2(-1, 0)
            if pressed[pg.K_RIGHT] or pressed[pg.K_d]:
                m += Vec2(1, 0)
            if m.length_squared() != 0:
                m = m.normalize() * SPEED
                player.pos += m
            self.rect.center = self.pos

    try:
        pygame.init()
        screen = pygame.display.set_mode((800, 450), pg.RESIZABLE, display=0)
        root_group = pg.sprite.RenderUpdates()
        player = Player()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise PGExit
                if event.type in (pg.KEYUP, pg.KEYDOWN) and event.key == pg.K_r:
                    screen.fill((0, 0, 0))
            root_group.update()
            # screen.fill((255, 255, 255))
            root_group.draw(screen)
            pg.display.flip()
            clock.tick(FPS)
    except PGExit:
        pass


if __name__ == '__main__':
    print('Hello world')
    main()
