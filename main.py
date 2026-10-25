import math
import sys
import pygame
import random
import time
from pygame.locals import *

from helpers.Effects import Effect
from helpers.utils import *
from helpers.config import *
from helpers.menus import * 
import objs.player as player
import objs.map as map
import objs.Camera as Camera
import objs.AudioManager as Audio

pygame.init()

pygame.display.update()

clock = pygame.time.Clock()

clock.tick(gameSpeed)

dim = Dimmer(255)

pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())] # creating joystick object

players = [player.Player([x + 100, 0]) for x in range(pygame.joystick.get_count())] # creating player objects from joystick objects
controllers = {}
playerDict = {}

t = 0

for i in range(len(joysticks)):
    controllers[i] = joysticks[i] # dictionary of joysticks so i can reference the id

for i in range(len(players)):
    playerDict[i] = players[i] # dictionary of players so i can reference their ids

print(playerDict)
Map = map.map() # creating map object
camera = Camera.Camera() # creating camera object
audio = Audio.AudioManager("assets/Boss Musics.wav")
# audio.load("assets/Boss Musics.wav")
# audio.play()

offset = [-400, -300]
scale_factor = [800, 600]
Exit = False

currentLen = len(playerDict)

while not Exit:
    center = camera.Centroid(playerDict) # calculates the center point between players for the camera to focus on
    scale_factor = camera.Scaling(playerDict)  # Works out the zoom level for the camera

    # setting zoom boundaries so the camera doesnt zoom in or out too much
    if scale_factor[0] < screen_width or scale_factor[1] < screen_height:
        scale_factor[0] = screen_width
        scale_factor[1] = screen_height
    if scale_factor[0] > screen_width * 2 or scale_factor[1] > screen_height * 2:
        scale_factor[0] = screen_width * 2
        scale_factor[1] = screen_height * 2

    deltaTime = clock.tick(gameSpeed)
    t += 1

    # pygame.draw.circle(surf, White, center, 5)

    scaled_surf = pygame.transform.scale(surf, scale_factor)
    surf.fill((0, 0, 0, 0))
    screen.fill(Grey)
    for item in backgrounds[background]:
        screen.blit(item, (0, 0))
        pass

    if len(controllers) == 0:
        y = 5 * math.sin(t / 11) + 280 # Y position of the text when no players are detected
        load_text("Please Connect a Controller", (255, 255, 255), (210, y), pygame.font.Font("assets/joystix.otf", 19), screen)
        scale_factor = [800, 600]
        offset = [400, 300]
        pass

    offset = camera.Offset(scale_factor)
    screen.blit(scaled_surf, (0 + offset[0], 0 + offset[1]))

    # trying to set the camera to follow the center of all the players
    camera.scroll[1] -= int((center[1] - (screen_height / 2)) / 15)
    camera.scroll[0] -= int((center[0] - (screen_width / 2)) / 15)

    # if you want to draw anything new to the screen, make sure that when you set its position
    # you add scroll to it i.e. pos[0] + scroll[0], pos[1] + scroll[1]
    # this will ensure that when the screen shakes, the object stays in the same place relative to everything else

    y = 0
    count = 0
    for key in playerDict.keys():
        y += 1
        pygame.draw.rect(screen, playerDict[key].color, (20, y * 28, 20, 20)) # draws cube next to players lives
        if playerDict[key].lives > 0:
            count += 1
            playerDict[key].Update(key, camera.scroll, surf, playerDict, Map.rects, controllers) # updates the players each frame
            load_text("Lives: ", White, (50, y * 28), pygame.font.Font("assets/joystix.otf", 14), screen)
            load_text(str(playerDict[key].lives), White, (125, y * 28), pygame.font.Font("assets/joystix.otf", 14), screen)
        else:
            load_text("Out: ", White, (50, y * 28), pygame.font.Font("assets/joystix.otf", 14), screen)


    if count == 1 and len(playerDict) > 1: # Loads ending screen when all the players are defeated
        Pause(surf, playerDict, controllers, Map, key, True)
        from helpers.menus import background # needed to change what the current background is if choosing a different map


    elif count == 1 and len(playerDict) == 1: # if there is only one player then the lives dont go down
        for key in playerDict.keys():
            if playerDict[key].lives != 3:
                playerDict[key].lives = 3


    Map.Draw(surf, camera.scroll)   # drawing the map each frame
    Effect.drawShockwave(surf)      # drawing the shockwaves should there be any

    # event handler for key/joystick presses
    try:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                Exit = True

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_k:
                    Map.map = Map.txtLoadMap("assets/new.txt")
                if event.key == pygame.K_ESCAPE:
                    Exit = True
                if event.key == pygame.K_c:
                    for key in playerDict.keys():
                        playerDict[key].dash = True

                if event.key == pygame.K_KP_ENTER:
                    playerDict[99] = player.Player([100, 100], keyboard=True)
                    controllers[99] = None

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    players[0].Jump = False

            # independently handling each joystick object (you know this)
            # 0 = A 1 = B 2 = X 3 = Y 4 = LB 5 = RB 6 = Select 7 = Start 8 = LStick 9 = RStick 10 = xbox
            for keys in controllers.keys():
                if playerDict[keys].lives > 0 and not playerDict[keys].keyboard:
                    if event.type == pygame.JOYBUTTONDOWN:
                        if controllers[keys].get_button(0):
                            try:
                                playerDict[keys].Jump = True
                            except IndexError:
                                print("out of range")
                        if controllers[keys].get_button(1):
                            playerDict[keys].color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)
                        if controllers[keys].get_button(2):
                            playerDict[keys].dash = True
                        if controllers[keys].get_button(3) and playerDict[keys].vel[1] != 0:
                            playerDict[keys].down_attack = True
                        if controllers[keys].get_button(7) or controllers[keys].get_button(6):
                            controllers[keys].get_name()
                            dim.dim()
                            Pause(surf, playerDict, controllers, Map, keys)
                            from helpers.menus import background
                            dim.undim()

                    if event.type == pygame.JOYBUTTONUP:
                        if not controllers[keys].get_button(0):
                            try:
                                playerDict[keys].Jump = False
                            except IndexError:
                                print("out of range")

                    # print(joystick.get_name(), joystick.get_axis(0))
                    if event.type == pygame.JOYAXISMOTION:
                        if controllers[keys].get_axis(0) < -0.5:
                            # Facing 1 means going left
                            playerDict[keys].facing = 1
                            playerDict[keys].vel[0] = -7
                        elif controllers[keys].get_axis(0) > 0.5:
                            playerDict[keys].facing = 0
                            playerDict[keys].vel[0] = 7
                            playerDict[keys].moving = True
                        else:
                            if not playerDict[keys].hit:
                                playerDict[keys].vel[0] = 0
                                playerDict[keys].moving = False

            if event.type == pygame.JOYDEVICEADDED:
                try:
                    joy = pygame.joystick.Joystick(event.device_index)
                    joy.rumble(0, 0.7, 500)
                    playerDict[joy.get_instance_id()] = player.Player([random.randint(100, 500), 0])

                    joysticks.append(joy)
                    print("add", playerDict)
                    controllers[joy.get_instance_id()] = joy
                except pygame.error:
                    load_text("Error Loading Joystick", White, (300, 400), pygame.font.Font("assets/joystix.otf"), screen)

            if event.type == pygame.JOYDEVICEREMOVED:
                print("remove", playerDict)
                if event.instance_id in controllers.keys():
                    del controllers[event.instance_id]
                    del playerDict[event.instance_id]
    except SystemError:
        pass
    
    pygame.display.update()
pygame.quit()
sys.exit()