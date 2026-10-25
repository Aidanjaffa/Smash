import sys
from helpers.config import White, screen, screen_width
import pygame
from helpers.utils import *

background = 0

def Pause(surf, playerDict, controllers, Map, key, win=False):
    global background
    exit = False

    offset_px = 50

    map1 = pygame.transform.scale(pygame.image.load("assets/map.png"), (996 / 7, 750 / 7))
    map2 = pygame.transform.scale(pygame.image.load("assets/Map2_back.png"), (996 / 7, 750 / 7))
    map3 = pygame.transform.scale(pygame.image.load("assets/map3_back.png"), (996 / 7, 750 / 7))  # width = 142.3

    map1_outline = pygame.Rect(70 - 10 + offset_px, 70 - 10, 996 / 7 + 20, 750 / 7 + 20)
    map2_outline = pygame.Rect(400 + offset_px - 10 - (map2.get_width() / 2), 70 - 10, 996 / 7 + 20, 750 / 7 + 20)
    map3_outline = pygame.Rect(400 - 10 + offset_px + (330 - map2.get_width()), 70 - 10, 996 / 7 + 20, 750 / 7 + 20)
    map4_outline = pygame.Rect(400 - 10 + offset_px + (600 - map2.get_width()), 70 - 10, 996 / 7 + 20, 750 / 7 + 20)

    MenuItems = [[map1_outline, 
                  map2_outline,  
                  map3_outline, 
                  map4_outline],
                 [pygame.Rect(497, 500, 230, 25)]]

    x = 0
    y = 0
    t = 0

    move = False
    right = False
    left = False
    while not exit:
        surf.fill((0, 0, 0, 0))

        draw_rounded_rect(surf, map1_outline, (73, 145, 22), 10)
        draw_rounded_rect(surf, map2_outline, (73, 145, 22), 10)
        draw_rounded_rect(surf, map3_outline, (73, 145, 22), 10)
        draw_rounded_rect(surf, map4_outline, (73, 145, 22), 10)

        draw_rounded_rect(surf, MenuItems[x][y], White, 10)
        load_text("Press Start to Return to Game", (255, 255, 255), (screen_width / 2 - 220, 500), pygame.font.Font("assets/joystix.otf", 19), screen)
        load_text("Press Select to Exit", (255, 255, 255), (screen_width / 2 - 160, 520), pygame.font.Font("assets/joystix.otf", 19), screen)

        # Controls Text
        load_text("Controls", (255, 255, 255), (120, 215), pygame.font.Font("assets/joystix.otf", 21), screen)
        load_text("A = Jump", (255, 255, 255), (125, 243), pygame.font.Font("assets/joystix.otf", 16), screen)
        load_text("B = Down Attack", (255, 255, 255), (125, 266), pygame.font.Font("assets/joystix.otf", 16), screen)
        load_text("X = Dash", (255, 255, 255), (125, 289), pygame.font.Font("assets/joystix.otf", 16), screen)
        load_text("Y = Change Colour", (255, 255, 255), (125, 312), pygame.font.Font("assets/joystix.otf", 16), screen)

        surf.blit(map1, (70 + offset_px, 70))
        surf.blit(map2, (400 - (map2.get_width() / 2) + offset_px, 70))
        surf.blit(map3, (400 + (330 - (map3.get_width())) + offset_px, 70))
        screen.blit(surf, (0, 0))
        t += 1
        if win:
            for key in playerDict.keys():
                if playerDict[key].lives > 0:
                    draw_rounded_rect(screen, pygame.Rect(330, 400, 190, 35), playerDict[key].color, 5)
                    load_text("WINNER", (255, 255, 255), (350, 400), pygame.font.Font("assets/joystix.otf", 30), screen)

        right = False
        left = False

        for controller in controllers.values():
            if controller.get_axis(0) > 0.5:
                right = True
            elif controller.get_axis(0) < -0.5:
                left = True

        if right and not move:
            y += 1
            if y > 3:
                y = 3
            move = True
        elif left and not move:
            y -= 1
            if y < 0:
                y = 0
            move = True
        
        if -0.5 <= controller.get_axis(0) <= 0.5:
            move = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            for key in controllers.keys():
                if event.type == pygame.JOYBUTTONDOWN:
                    if controllers[key].get_button(7):
                        exit = True
                    if controllers[key].get_button(0):
                        num = str(y + 1)
                        choice = "assets/map" + num + ".png"
                        Map.map = Map.load_map(choice)
                        exit = True

                        for key in playerDict.keys():
                            playerDict[key].pos = [100, 0]
                            playerDict[key].vel = [0, 0]
                            playerDict[key].lives = 3
                            background = int(num) -1

                    if controllers[key].get_button(6):
                        sys.exit()

                
        pygame.display.update()