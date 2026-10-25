import pygame
import random
import math
from helpers.Effects import Effect
from helpers.utils import *


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
        self.lives = 3
        self.vel = [0, 0]
        self.rect = pygame.Rect(self.vel[0], self.vel[1], 10 * 2, 16 * 2)
        self.surf = pygame.Surface((0,0))
        self.scroll = [0, 0]

        self.swordAngle = 16
        self.sword = pygame.transform.rotate(self.sword, self.swordAngle)
        self.swordL = pygame.transform.rotate(self.swordL, self.swordAngle)
        self.swordD = pygame.transform.rotate(self.swordL, 90)

        self.Jump = False
        self.impact = False
        self.colliding = False
        self.shake = False
        self.dash = False
        self.moving = False
        self.moving_right = False
        self.moving_left = False

        # 1 = Left 0 = Right
        self.facing = 0

        self.impactCount = 0
        self.dashCount = 0
        self.cooldown = 0
        self.ID = None
        self.hit = False
        self.air_timer = 0
        self.player_y_momentum = 0
        self.goal = 0
        self.t = 0
        self.hitter = None

        self.color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 0)

        self.afterImages = []
        self.sword_clashs = [pygame.mixer.Sound("assets/sword.wav"), pygame.mixer.Sound("assets/Sword2t.wav")]
        self.dash_sound = pygame.mixer.Sound("assets/dash.wav")

        self.slomo_cooldown = 20
        self.slomo = False
        self.down_attack = False
        pass
 
    def Update(self, ID, scroll, surf, playerDict, map, controllers):
        global gameSpeed
        # this block colors in the player by blending a tint with the sprite
        # it also chooses whether it should show the standing sprite or the jumping sprite
        self.ID = ID
        self.surf = surf
        self.scroll = scroll

        tint = self.applyTints(self.facing, surf, scroll) # returns the tint to be used in other methods but also draws player and tint
        
        if not self.hit: # this code is the player being hit not doing the hitting
            for keys in playerDict.keys():
                if playerDict[keys].ID != self.ID:
                    if self.rect.colliderect(playerDict[keys].rect) and playerDict[keys].dash and self.dashCount <= 0:
                        self.hit = True
                        self.t = 0
                        self.vel[0] += 10
                        self.hitter = playerDict[keys].ID
                        if playerDict[keys].facing != self.facing:
                            self.sword_clashs[random.randint(0, 1)].play()
                            Effect.addShockwave(self.pos[0] + scroll[0], self.pos[1] + scroll[1], 0, 12)
                            self.slomo_cooldown = 10
                            self.slomo = True
                   
                    elif self.rect.colliderect(playerDict[keys].rect) and playerDict[keys].down_attack:
                        Effect.addShockwave(self.pos[0] + scroll[0], self.pos[1] + scroll[1], 0, 12)
                        self.slomo_cooldown = 10
                        self.slomo = True
                        self.hit = True
                        self.t = 0
                        self.hitter = playerDict[keys].ID
                        self.vel[0] += 10
                        playerDict[keys].facing = self.facing

        elif self.hit:
            self.t += 1
            if self.facing == playerDict[self.hitter].facing:
                self.vel[0] = self.Hit(30, self.vel[0], playerDict[self.hitter].facing)
            else:
                self.vel[0] = self.Hit(10, self.vel[0], playerDict[self.hitter].facing)
                playerDict[self.hitter].vel[0] = -playerDict[self.hitter].Hit(4, playerDict[self.hitter].vel[0], 1)
                playerDict[self.hitter].dashCount = 0
                playerDict[self.hitter].dash = False

        # this makes sure the sword is facing the right way when moving as the sword sprite is drawn seperatly
        # as to not be blended with the sprite itself
        if not self.down_attack:
            if self.facing == 0:
                surf.blit(self.sword, (self.pos[0] + 10 + scroll[0], self.pos[1] + 5 + scroll[1]))
            elif self.facing == 1:
                surf.blit(self.swordL, (self.pos[0] - 30 + scroll[0], self.pos[1] + 5 + scroll[1]))
        else:
            surf.blit(self.swordD, (self.pos[0] + scroll[0], self.pos[1] + 15 + scroll[1]))

        # Player hitbox
        self.rect = pygame.Rect(self.pos[0] + scroll[0], self.pos[1] + scroll[1], 20, 32)
        # pygame.draw.rect(surf, White, self.rect, 1)

        self.Dash(tint, playerDict, scroll)

        # Updating the players positions based on the velocities
        self.pos[1] += self.vel[1]
        self.pos[0] += self.vel[0]

        # Gravity strength and terminal velocity
        if not self.colliding:
            self.vel[1] += 1.3
        if self.vel[1] > 50:
            self.vel[1] = 50

        # Wrapping the screen
        if self.pos[1] > 1500 + scroll[1]:
            self.pos[1] = 0
            self.pos[0] = random.randint(0, 800)
            self.lives -= 1
        #self.pos[0] = (850 + self.pos[0]) % 850
        #self.pos[1] = (screen_height + self.pos[1]) % screen_height

        if self.slomo:
            gameSpeed = 30
            self.slomo_cooldown -= 1
            if self.slomo_cooldown <= 0:
                gameSpeed = 60
                self.slomo = False

        if self.down_attack:
            self.vel[1] = 35

        self.Impact(map, controllers, scroll)
        # i put collide here so that at the end of the frame colliding gets updated
        # so its useful for the shaking stuff
        self.collide(scroll, map)
        pass

    def collide(self, scroll, map):
        # colliding is false unless player is touching a block(for screenshaking)
        self.colliding = False
        # every frame it iterates over each tile and checks if that rect collides with the players hitbox
        # then the players y vel is set 0 and the player is moved to the top of the block - scroll[1](idk it just works)
        # then i have cheap dirty jumping which moves the player off the block so vel isnt set to 0 and the player
        # pos is not reset, then there is a boost in Y vel so it jumps up
        for item in map:
            if self.rect.colliderect(item):
                if self.vel[1] > 1:
                    self.vel[1] = 0
                    self.pos[1] = item.top - 31 - scroll[1]
                    self.colliding = True
                    if self.Jump:
                        self.vel[1] -= 18
                        self.pos[1] -= 1
                    if self.down_attack:
                        self.down_attack = False

    def AfterImage(self, tint, scroll):
        for sprite in self.afterImages:
            self.surf.blit(self.sprites[self.facing][0], (sprite[0] + scroll[0], sprite[1] + scroll[1]))
            self.surf.blit(tint, (sprite[0] + scroll[0], sprite[1] + scroll[1]), special_flags=pygame.BLEND_RGBA_MULT)
            self.sprites[self.facing][0].set_alpha(sprite[2])
            tint.set_alpha(sprite[2])
            sprite[2] -= 10
            if sprite[2] <= 0:
                self.afterImages.remove(sprite)
        pass

    def Impact(self, map, controllers, scroll):
        # Impact is if the player is touching this frame, colliding is in the last frame
        # When the player lands for one frame impact will be true and colliding will be false
        self.impact = False
        for item in map:
            if item.colliderect(self.rect):
                self.impact = True

        # This registers that the player his hit the floor at a given speed and will initiate the shake countdown
        if self.impact and not self.colliding and self.vel[1] > 25:
            self.impactCount = 10
            self.shake = True

        # if impactCount > 0 then it should shake the screen
        if self.impactCount > 0:
            self.impactCount -= 1
            for key in controllers.keys():
                controllers[key].rumble(0, 5, 5)
            self.shake = False

    def Dash(self, tint, playerDict, scroll):
        # THIS CODE IS FRAGILE ASF. Please try not to mess with it too much
        # just incase heres an explanation

        # After Image shit for when you dash

        # This block makes it so that when you are dashing it leaves behind after images that fade away
        # it makes sure there are only 10 after images stored and it keeps it like a queue so FIFO and if it is
        # > 0 that means dashing is occuring so the after image method is called

        if len(self.afterImages) > 10:
            self.afterImages.pop(0)
        if len(self.afterImages) > 0:
            self.AfterImage(tint, scroll)

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
            elif self.facing == 0:
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
                    self.vel[0] = -7
                else:
                    self.vel[0] = 7

        #cooldown for the dash so you cant spam it
        if self.cooldown > 0:
            self.cooldown -= 1
            self.dash = False

    def Hit(self, intial, current, facing):
        #v(t) = velocity at time, v_0 = intial velocity, e base log, k = decay constant
        decay = 0.1
        if abs(current) <= 1:
            self.hit = False
            return 0
        elif abs(current) > 0 and facing == 1:
            current = intial * math.e**(-decay * self.t)
            return -current
        elif abs(current) > 0 and facing == 0:
            current = intial * math.e**(-decay * self.t)
            return current

    def applyTints(self, facing, surf, scroll):
        tint = pygame.Surface((10 * 2, 16 * 2), pygame.SRCALPHA)
        tint.fill((self.color[0], self.color[1], self.color[2], 255))
        surf.blit(self.sprites[facing][0], (self.pos[0] + scroll[0], self.pos[1] + scroll[1]))
        surf.blit(tint, (self.pos[0] + scroll[0], self.pos[1] + scroll[1]),
                    special_flags=pygame.BLEND_RGBA_MULT)
        if self.dashCount > 0:
            self.afterImages.append([self.pos[0], self.pos[1], 255])
        
        return tint