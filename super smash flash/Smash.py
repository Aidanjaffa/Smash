import pygame
from pygame.locals import *
import random
pygame.init()

screen_width = 800
screen_height = 600

screen = pygame.display.set_mode((screen_width, screen_height))

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
        self.playerL = pygame.transform.flip(self.player, True, False)
        self.playerJumpL = pygame.transform.flip(self.playerJump, True, False)
        self.sword = pygame.transform.scale(pygame.image.load("assets/sword.png").convert_alpha(), (16 * 2, 10 * 2))
        self.swordL = pygame.transform.flip(self.sword, True, False)

        # 2D array of all the sprites that the player will use, [0] is for right facing, [1] is left facing
        self.sprites = [[pygame.transform.scale(self.player, (10 * 2, 16 * 2)),
                        pygame.transform.scale(self.playerJump, (10 * 2, 16 * 2))],
                        [pygame.transform.scale(self.playerL, (10 * 2, 16 * 2)),
                         pygame.transform.scale(self.playerJumpL, (10 * 2, 16 * 2))]]

        self.pos = pos
        self.vel = [0, 0]
        self.rect = pygame.Rect(self.pos[0], self.pos[1], 20, 32)
        self.swordAngle = 16
        self.sword = pygame.transform.rotate(self.sword, self.swordAngle)
        self.swordL = pygame.transform.rotate(self.swordL, self.swordAngle)

        self.Jump = False
        self.impact = False
        self.colliding = False
        self.shake = False
        self.dash = False
        self.moving = False

        # 1 = Left 0 = Right
        self.facing = 1

        self.impactCount = 0
        self.dashCount = 0
        self.cooldown = 0

        self.color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 0)

        self.afterImages = []
        pass

    def Draw(self, ID):
        # this block colors in the player by blending a tint with the sprite
        # it also chooses whether it should show the standing sprite or the jumping sprite
        if not self.Jump:
            tint = pygame.Surface((10 * 2, 16 * 2), pygame.SRCALPHA)
            tint.fill((self.color[0], self.color[1], self.color[2], 0))
            screen.blit(self.sprites[self.facing][0], (self.pos[0] + scroll[0], self.pos[1] + scroll[1]))
            screen.blit(tint, (self.pos[0] + scroll[0], self.pos[1] + scroll[1]), special_flags=pygame.BLEND_RGBA_MULT)
            if self.dashCount > 0:
                self.afterImages.append([self.pos[0] + scroll[0], self.pos[1] + scroll[1], 255])

        elif self.Jump:
            tint = pygame.Surface((10 * 2, 16 * 2), pygame.SRCALPHA)
            tint.fill((self.color[0], self.color[1], self.color[2], 0))
            screen.blit(self.sprites[self.facing][1], (self.pos[0] + scroll[0], self.pos[1] + scroll[1]))
            screen.blit(tint, (self.pos[0] + scroll[0], self.pos[1] + scroll[1]), special_flags=pygame.BLEND_RGBA_MULT)
            if self.dashCount > 0:
                self.afterImages.append([self.pos[0] + scroll[0], self.pos[1] + scroll[1], 255])

        # this makes sure the sword is facing the right way when moving as the sword sprite is drawn seperatly
        # as to not be blended with the sprite itself
        if self.facing == 0:
            screen.blit(self.sword, (self.pos[0] + 10 + scroll[0], self.pos[1] + 5 + scroll[1]))
        elif self.facing == 1:
            screen.blit(self.swordL, (self.pos[0] - 30 + scroll[0], self.pos[1] + 5 + scroll[1]))

        # Player hitbox
        self.rect = pygame.Rect(self.pos[0] + scroll[0], self.pos[1] + scroll[1], 20, 32)

        self.Dash(tint)

        # Updating the players positions based on the velocities
        self.pos[1] += self.vel[1]
        self.pos[0] += self.vel[0]

        # Gravity strength and terminal velocity
        self.vel[1] += 0.5
        if self.vel[1] > 50:
            self.vel[1] = 50

        # Wrapping the screen
        self.pos[0] = (screen_width + self.pos[0]) % screen_width
        self.pos[1] = (screen_height + self.pos[1]) % screen_height

        self.Impact()
        # i put collide here so that at the end of the frame colliding gets updated
        # so its useful for the shaking stuff
        self.collide(ID)
        pass

    def collide(self, ID):
        # colliding is false unless player is touching a block(for screenshaking)
        self.colliding = False
        # every frame it iterates over each tile and checks if that rect collides with the players hitbox
        # then the players y vel is set 0 and the player is moved to the top of the block - scroll[1](idk it just works)
        # then i have cheap dirty jumping which moves the player off the block so vel isnt set to 0 and the player
        # pos is not reset, then there is a boost in Y vel so it jumps up
        for item in Map.rects:
            if self.rect.colliderect(item):
                self.vel[1] = 0
                self.pos[1] = item.top - 31 - scroll[1]
                # controllers[ID].rumble(0, 0.7, 500)
                self.colliding = True
                if self.Jump:
                    self.vel[1] -= 12
                    self.pos[1] -= 1
                    # self.colliding = False

    def AfterImage(self, tint):
        for sprite in self.afterImages:
            screen.blit(self.sprites[self.facing][0], (sprite[0], sprite[1]))
            screen.blit(tint, (sprite[0], sprite[1]), special_flags=pygame.BLEND_RGBA_MULT)
            self.sprites[self.facing][0].set_alpha(sprite[2])
            tint.set_alpha(sprite[2])
            sprite[2] -= 10
            if sprite[2] <= 0:
                self.afterImages.remove(sprite)
        pass

    def Impact(self):
        # Impact is if the player is touching this frame, colliding is in the last frame
        # When the player lands for one frame impact will be true and colliding will be false
        self.impact = False
        for item in Map.rects:
            if item.colliderect(self.rect):
                self.impact = True

        # This registers that the player his hit the floor at a given speed and will initiate the shake countdown
        if self.impact and not self.colliding and self.vel[1] > 16:
            self.impactCount = 10
            self.shake = True

        # if impactCount > 0 then it should shake the screen
        if self.impactCount > 0:
            self.impactCount -= 1
            ScreenShake(10)
            for key in controllers.keys():
                controllers[key].rumble(0, 5, 5)
            self.shake = False

    def Dash(self, tint):
        # THIS CODE IS FRAGILE ASF. Please try not to mess with it too much
        # just incase heres an explanation

        # After Image shit for when you dash

        # This block makes it so that when you are dashing it leaves behind after images that fade away
        # it makes sure there are only 10 after images stored and it keeps it like a queue so FIFO and if it is
        # > 0 that means dashing is occuring so the after image method is called
        if len(self.afterImages) > 10:
            self.afterImages.pop(0)
        if len(self.afterImages) > 0:
            self.AfterImage(tint)

        # Fading by setting the alpha
        if len(self.afterImages) == 0:
            self.sprites[self.facing][0].set_alpha(255)

        # so when the dash button is pressed dash is set to true. now at this point the player is probably not dashing
        # so dashCount is set to 10, if dash is true and we didnt check cooldown and dashCount it would continuously
        # set dashcount to 10 and therefore the player would never stop
        if self.dash and self.cooldown == 0 and self.dashCount <= 0:
            self.dashCount = 10

        # When dashCount is above 0. It'll start decrementing it frame by frame and adjust the players xvel to 20 in
        # the corresponding direction. while dashcount is above 0, then the velocity will keep getting set until
        # dashcount reaches 0. once that happens the cooldown starts

        if self.dashCount > 0:
            self.dashCount -= 1
            if self.facing == 1:
                self.vel[0] = -20
            else:
                self.vel[0] = 20

            if self.dashCount == 0:
                self.cooldown = 20

        # Here the order of the code is very important and this is to ensure smooth movement if the player is holding
        # a direction. When dash is true and cooldown is > 0 then the player xvel = 0 (this only occurs on the frame
        # when the player stops dashing )however (and this is the jank
        # i wrote) a new flag called moving is set to true or false down in the game loop depending on whether
        # the player is moving. this means that the player wont just stop mid movement. I hope that makes sense
        if self.dash and self.cooldown > 0:
            self.vel[0] = 0
            if self.moving:
                if self.facing == 1:
                    self.vel[0] = -5
                else:
                    self.vel[0] = 5

        #cooldown for the dash so you cant spam it
        if self.cooldown > 0:
            self.cooldown -= 1
            self.dash = False



class map:
    def __init__(self):
        self.map = self.load_map()
        # dictionary of the tile sprites
        self.sprites = {"grass": pygame.image.load("assets/grass.png"),
                        "dirt": pygame.image.load("assets/dirt1.png")}
        # all the tiles from the 2d array get put into a 1d array so i dont need 2 for loops for iteration
        # also are turned into pygame.rect objects for ease of collision checking
        self.rects = []
        pass

    def Draw(self):
        # rects is reset every time other wise it gets laggy
        self.rects = []
        # x and y are set to -1 so we get 1 column of blocks outside the screen so when the screenshakes it doesnt look
        # weird

        # then this iterates through the 2d array that was returned from load_map() for each line and tile
        # each iteration of the for loop is incrementing its own axis by 1. the axis is multiplied by the size i
        # want the blocks to be. it checks if that item corrosponds and draws the tile where needed.
        y = -1
        for line in self.map:
            x = -1
            for block in line:
                if block == 'g':
                    screen.blit(self.sprites["grass"], (x * 50 + scroll[0], y * 50 + scroll[1]))
                    self.rects.append(pygame.Rect(x * 50 + scroll[0], y * 50 + scroll[1], 50, 50))
                if block == 'd':
                    screen.blit(self.sprites["dirt"], (x * 50 + scroll[0], y * 50 + scroll[1]))
                    self.rects.append(pygame.Rect(x * 50 + scroll[0], y * 50 + scroll[1], 50, 50))

                x += 1
            y += 1
        pass

    # i think pretty self-explanatory
    def load_map(self):
        f = open("assets/map.txt", "r")
        data = f.read()
        f.close()
        data = data.split("\n")
        map = []
        for row in data:
            map.append(list(row))
        return map


# this too
def ScreenShake(screenshake):
    if screenshake > 0:
        screenshake -= 1

    if screenshake:
        scroll[0] += random.randint(0, 16) - 8
        scroll[1] += random.randint(0, 16) - 8


# you know most of this as you helped me out
pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]

players = [Player([x + 500, 100]) for x in range(pygame.joystick.get_count())]
controllers = {}
playerDict = {}

for i in range(len(joysticks)):
    controllers[i] = joysticks[i]

for i in range(len(players)):
    playerDict[i] = players[i]

print(playerDict)
Map = map()

scroll = [0, 0]
Exit = False
frame = 0

while not Exit:
    deltaTime = clock.tick(60)

    screen.fill(Grey)
    Map.Draw()

    # if the screenshaking gets a bit too much then scroll is set to 0 so the tiles dont go too far offscreen
    # BTW IMPORTANT if you want to draw anything new to the screen, make sure that when you set its position
    # you add scroll to it i.e. pos[0] + scroll[0], pos[1] + scroll[1]
    # this will ensure that when the screen shakes, the object stays in the same place relative to everything else
    if scroll[0] > 30 or scroll[0] < -30:
        scroll[0] = 0
    if scroll[1] > 30 or scroll[1] < -30:
        scroll[1] = 0

    for key in playerDict.keys():
        playerDict[key].Draw(key)

    # event handler for key/joystick presses
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
            if event.key == pygame.K_c:
                for key in playerDict.keys():
                    playerDict[key].dash = True

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_SPACE:
                players[0].Jump = False

        # independently handling each joystick object (you know this)
        # 0 = A 1 = B 2 = X 3 = Y 4 = LB 5 = RB 6 = Select 7 = Start 8 = LStick 9 = RStick 10 = xbox
        for keys in controllers.keys():
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
                    # Facing 1 means going left
                    playerDict[keys].facing = 1
                    playerDict[keys].moving = True
                elif controllers[keys].get_axis(0) > 0.5:
                    playerDict[keys].vel[0] = 5
                    playerDict[keys].facing = 0
                    playerDict[keys].moving = True
                else:
                    playerDict[keys].vel[0] = 0
                    playerDict[keys].moving = False

        if event.type == pygame.JOYDEVICEADDED:
            joy = pygame.joystick.Joystick(event.device_index)
            joy.rumble(0, 0.7, 500)
            playerDict[joy.get_instance_id()] = Player([400, 100])

            joysticks.append(joy)
            print("add", playerDict)
            controllers[joy.get_instance_id()] = joy

        if event.type == pygame.JOYDEVICEREMOVED:
            print("remove", playerDict)
            if event.instance_id in controllers.keys():
                del controllers[event.instance_id]
                del playerDict[event.instance_id]

    pygame.display.update()

pygame.quit()
quit()
