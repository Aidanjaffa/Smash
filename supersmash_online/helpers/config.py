import pygame
from pygame.locals import *

screen_width = 1200
screen_height = 720
Black = (0, 0, 0)
White = (255, 255, 255)
Grey = (70, 70, 70)
gameSpeed = 60

screen = pygame.display.set_mode((screen_width, screen_height))#, FULLSCREEN | SCALED)
surf = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)

# backgrounds = [[pygame.transform.scale(pygame.image.load("assets/Lv1_BG1.png").convert_alpha(), (screen_width,
#                                                                                                  screen_height))],
#                [pygame.transform.scale(pygame.image.load("assets/Background2.png").convert_alpha(), (screen_width,
#                                                                                                      screen_height)),
#                 pygame.transform.scale(pygame.image.load("assets/Lv2_BG3.png").convert_alpha(), ((screen_width * 2) * 2
#                                                                                                  - 600, (screen_height / 2) * 2))],
#                [pygame.transform.scale(pygame.image.load("assets/Lv3_BG1.png").convert_alpha(), (screen_width,
#                                                                                                  screen_height)),
#                 pygame.transform.scale(pygame.image.load("assets/Lv3_BG2.png").convert_alpha(), ((screen_width * 2) * 2
#                                                                                                  - 600, (screen_height / 2) * 2))]]