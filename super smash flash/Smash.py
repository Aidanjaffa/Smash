import pygame
from pygame.locals import *
import random
pygame.init()

screen_width = 800
screen_height = 600

screen = pygame.display.set_mode((screen_width, screen_height), FULLSCREEN)

pygame.display.update()

Black = (0, 0, 0)
White = (255, 255, 255)
Grey = (30, 30, 30)

clock = pygame.time.Clock()

clock.tick(60)


class Player(object):
    def __init__(self, pos):
        self.player = pygame.image.load("assets/horatioStand.png").convert_alpha()
        self.playerJump = pygame.image.load("assets/horatioJump.png").convert_alpha()
        self.sword = pygame.transform.scale(pygame.image.load("assets/sword.png").convert_alpha(), (16 * 2, 10 * 2))

        self.sprites = [pygame.transform.scale(self.player, (10 * 2, 16 * 2)),
                        pygame.transform.scale(self.playerJump, (10 * 2, 16 * 2))]

        self.pos = pos
        self.vel = [0, 0]
        self.rect = pygame.Rect(self.pos[0], self.pos[1], 20, 32)
        self.swordAngle = 16
        self.sword = pygame.transform.rotate(self.sword, self.swordAngle)

        self.Jump = False
        self.color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)
        pass

    def Draw(self, ID):
        self.collide(ID)
        if not self.Jump:
            tint = pygame.Surface((10 * 2, 16 * 2))
            tint.fill(self.color)
            screen.blit(self.sprites[0], self.pos)
            screen.blit(tint, self.pos, special_flags=pygame.BLEND_RGBA_MULT)

        elif self.Jump:
            tint = pygame.Surface((10 * 2, 16 * 2))
            tint.fill(self.color)
            screen.blit(self.sprites[1], self.pos)
            screen.blit(tint, self.pos, special_flags=pygame.BLEND_RGBA_MULT)

        screen.blit(self.sword, (self.pos[0] + 10, self.pos[1] + 5))

        self.rect = pygame.Rect(self.pos[0], self.pos[1], 20, 32)
        # pygame.draw.rect(screen, White, self.rect, 1)

        self.pos[1] += self.vel[1]
        self.pos[0] += self.vel[0]

        self.vel[1] += 0.5
        if self.vel[1] > 50:
            self.vel[1] = 50

        self.pos[0] = (screen_width + self.pos[0]) % screen_width
        self.pos[1] = (screen_height + self.pos[1]) % screen_height
        pass

    def collide(self, ID):
        for item in Map.rects:
            if self.rect.colliderect(item):
                self.vel[1] = 0
                self.pos[1] = item.top - 31
                # controllers[ID].rumble(0, 0.7, 500)
                if self.Jump:
                    self.vel[1] -= 12
                    self.pos[1] -= 1


class map:
    def __init__(self):
        self.map = self.load_map()
        self.sprites = {"grass": pygame.image.load("assets/grass.png"),
                        "dirt": pygame.image.load("assets/dirt1.png")}
        self.rects = []
        pass

    def Draw(self):
        self.rects = []
        y = 0
        for line in self.map:
            x = 0
            for block in line:
                if block == 'g':
                    screen.blit(self.sprites["grass"], (x * 50, y * 50))
                    self.rects.append(pygame.Rect(x * 50, y * 50, 50, 50))
                if block == 'd':
                    screen.blit(self.sprites["dirt"], (x * 50, y * 50))
                    self.rects.append(pygame.Rect(x * 50, y * 50, 50, 50))

                x += 1
            y += 1
        pass

    def load_map(self):
        f = open("assets/map.txt", "r")
        data = f.read()
        f.close()
        data = data.split("\n")
        map = []
        for row in data:
            map.append(list(row))
        return map


pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]

players = [Player([x + 100, 100]) for x in range(pygame.joystick.get_count())]
controllers = {}
playerDict = {}

for i in range(len(joysticks)):
    controllers[i] = joysticks[i]

for i in range(len(players)):
    playerDict[i] = players[i]

print(playerDict)
Map = map()
Exit = False

while not Exit:
    screen.fill(Grey)
    Map.Draw()
    for key in playerDict.keys():
        playerDict[key].Draw(key)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            Exit = True

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_k:
                Map.map = Map.load_map()
            if event.key == pygame.K_SPACE:
                players[0].Jump = True
            if event.key == pygame.K_ESCAPE:
                Exit = True

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_SPACE:
                players[0].Jump = False

        for keys in controllers.keys():
            if event.type == pygame.JOYBUTTONDOWN:
                if controllers[keys].get_button(0):
                    try:
                        playerDict[keys].Jump = True
                    except IndexError:
                        print("out of range")
                if controllers[keys].get_button(1):
                    playerDict[keys].color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)

            if event.type == pygame.JOYBUTTONUP:
                if not controllers[keys].get_button(0):
                    try:
                        playerDict[keys].Jump = False
                    except IndexError:
                        print("out of range")

            # print(joystick.get_name(), joystick.get_axis(0))
            if event.type == pygame.JOYAXISMOTION:
                if controllers[keys].get_axis(0) < -0.5:
                    playerDict[keys].vel[0] = -5
                elif controllers[keys].get_axis(0) > 0.5:
                    playerDict[keys].vel[0] = 5
                else:
                    playerDict[keys].vel[0] = 0

        if event.type == pygame.JOYDEVICEADDED:
            joy = pygame.joystick.Joystick(event.device_index)
            joy.rumble(0, 0.7, 500)
            playerDict[joy.get_instance_id()] = Player([100, 100])

            joysticks.append(joy)
            print("add", playerDict)
            controllers[joy.get_instance_id()] = joy

        if event.type == pygame.JOYDEVICEREMOVED:
            print("remove", playerDict)
            if event.instance_id in controllers.keys():
                del controllers[event.instance_id]
                del playerDict[event.instance_id]


    pygame.display.update()
    clock.tick(60)

pygame.quit()
quit()
