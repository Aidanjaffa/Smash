import pygame
import pygame.gfxdraw
import random

class Dimmer:
    def __init__(self, keepalive=0):
        self.keepalive = keepalive
        if self.keepalive:
            self.buffer = pygame.Surface(pygame.display.get_surface().get_size())
        else:
            self.buffer = None

    def dim(self, darken_factor=64, color_filter=(0, 0, 0)):
        if not self.keepalive:
            self.buffer = pygame.Surface(pygame.display.get_surface().get_size())
        self.buffer.blit(pygame.display.get_surface(), (0, 0))
        if darken_factor > 0:
            darken = pygame.Surface(pygame.display.get_surface().get_size())
            darken.fill(color_filter)
            darken.set_alpha(darken_factor)
            # safe old clipping rectangle...
            old_clip = pygame.display.get_surface().get_clip()
            # ..blit over entire screen...
            pygame.display.get_surface().blit(darken, (0, 0))
            # ... and restore clipping
            pygame.display.get_surface().set_clip(old_clip)

    def undim(self):
        if self.buffer:
            pygame.display.get_surface().blit(self.buffer, (0, 0))
            pygame.display.flip()
            if not self.keepalive:
                self.buffer = None


def draw_rounded_rect(surface, rect, color, corner_radius):
    ''' Draw a rectangle with rounded corners.
    Would prefer this:
        pygame.draw.rect(surface, color, rect, border_radius=corner_radius)
    but this option is not yet supported in my version of pygame so do it ourselves.

    We use anti-aliased circles to make the corners smoother
    '''
    if rect.width < 2 * corner_radius or rect.height < 2 * corner_radius:
        raise ValueError(f"Both height (rect.height) and width (rect.width) must be > 2 * corner radius ({corner_radius})")

    # need to use anti aliasing circle drawing routines to smooth the corners
    pygame.gfxdraw.aacircle(surface, rect.left+corner_radius, rect.top+corner_radius, corner_radius, color)
    pygame.gfxdraw.aacircle(surface, rect.right-corner_radius-1, rect.top+corner_radius, corner_radius, color)
    pygame.gfxdraw.aacircle(surface, rect.left+corner_radius, rect.bottom-corner_radius-1, corner_radius, color)
    pygame.gfxdraw.aacircle(surface, rect.right-corner_radius-1, rect.bottom-corner_radius-1, corner_radius, color)

    pygame.gfxdraw.filled_circle(surface, rect.left+corner_radius, rect.top+corner_radius, corner_radius, color)
    pygame.gfxdraw.filled_circle(surface, rect.right-corner_radius-1, rect.top+corner_radius, corner_radius, color)
    pygame.gfxdraw.filled_circle(surface, rect.left+corner_radius, rect.bottom-corner_radius-1, corner_radius, color)
    pygame.gfxdraw.filled_circle(surface, rect.right-corner_radius-1, rect.bottom-corner_radius-1, corner_radius, color)

    rect_tmp = pygame.Rect(rect)

    rect_tmp.width -= 2 * corner_radius
    rect_tmp.center = rect.center
    pygame.draw.rect(surface, color, rect_tmp)

    rect_tmp.width = rect.width
    rect_tmp.height -= 2 * corner_radius
    rect_tmp.center = rect.center
    pygame.draw.rect(surface, color, rect_tmp)


def ScreenShake(screenshake, scroll):
    if screenshake > 0:
        screenshake -= 1

    if screenshake:
        scroll[0] += random.randint(0, 16) - 8
        scroll[1] += random.randint(0, 16) - 8


def load_text(message, colour, pos, font, screen):
    text = font.render(message, True, colour)
    screen.blit(text, pos)
    pass


