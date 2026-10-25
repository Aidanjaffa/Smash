import random
import pygame
import math
from collections import deque

class Player():
    def __init__(self, id):
        self.pos = [0, 0]
        self.vel = [0, 0]
        self.color = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
        self.id = id

        self.rect = [0, 0, 0, 0]

        self.colliding = False
        self.jump = False
        self.Dash = False
        self.moving = False
        self.hit = False

        self.cooldown = 0
        self.dashCount = 0

        self.facing = 0
        self.t = 0

        # Inbound input queue (one entry per client tick). game_loop drains it one
        # physics tick at a time so the server simulates the *same* per-tick input
        # stream the client predicted, never collapsing several inputs into a single
        # tick (which loses movement and snaps the client backward). cur_* hold the
        # last applied held-state, repeated on a starved tick to keep gravity going.
        self.input_queue = deque()
        self.last_ack = 0

    def apply_net_input(self):
        # Consume exactly ONE queued input and apply it for this physics tick.
        # Returns True if one was consumed. If the queue is empty we do NOT advance
        # this player this sub-tick (the caller skips update/dash), so the server
        # simulates exactly one tick per client input — never collapsing several
        # into one (which snapped the client backward) and never adding extra ticks
        # (which snapped it forward). That strict 1:1 mapping is what lets
        # reconcile() reproduce the client's prediction exactly.
        if not self.input_queue:
            return False

        data = self.input_queue.popleft()
        self.last_ack = data.get("seq", self.last_ack)

        # Skip movement during knockback so Hit() keeps control of vel[0].
        if not self.hit:
            self.vel[0] = 0
            self.moving = False
            if data.get("left", False):
                self.vel[0] = -15
                self.moving = True
                self.facing = 1
            elif data.get("right", False):
                self.vel[0] = 15
                self.moving = True
                self.facing = 0
        self.jump = data.get("jump", False)
        if data.get("dash", False) and not self.Dash:
            self.Dash = True
        return True

    def update(self, map, playerDict):
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]

        self.rect = [self.pos[0], self.pos[1], 10 * 2, 16 * 2]
        current_rect = pygame.Rect(self.rect)
    
        if self.t > 20:
            self.vel[0] = 0
            self.t = 0

        if not self.colliding:
            self.vel[1] += 3
        if self.vel[1] > 50:
            self.vel[1] = 50
        
        if not self.hit: # this code is the player being hit not the one doing the hitting
            for keys in playerDict.keys():
                other_player_rect = pygame.Rect(playerDict[keys].rect)
                if playerDict[keys].id != self.id: 
                    if current_rect.colliderect(other_player_rect) and playerDict[keys].Dash and self.dashCount <= 0: # if being hit
                        self.hit = True
                        self.t = 0
                        self.vel[0] += 10
                        self.hitter = playerDict[keys].id
                        playerDict[keys].vel[0] = 0
                        # if playerDict[keys].facing != self.facing:
                        #     self.slomo_cooldown = 30
                        #     self.slomo = True
                   
                    # elif self.rect.colliderect(playerDict[keys].rect) and playerDict[keys].down_attack:
                    #     self.slomo_cooldown = 30
                    #     self.slomo = True
                    #     self.hit = True
                    #     self.t = 0
                    #     self.hitter = playerDict[keys].ID
                    #     if self.facing == 0:
                    #         self.vel[0] += 10
                    #     elif self.facing == 1:
                    #         self.vel[0] -= 10
                        # playerDict[keys].facing = self.facing

        elif self.hit:
            self.t += 1
            if self.facing == playerDict[self.hitter].facing: # facing the same way meaning hit from behind
                self.vel[0] = self.Hit(50, self.vel[0], playerDict[self.hitter].facing, playerDict[self.hitter]) # person being hit
            else: # facing opposite ways, clashing swords
                self.vel[0] = self.Hit(15, self.vel[0], playerDict[self.hitter].facing, playerDict[self.hitter])
                playerDict[self.hitter].vel[0] = -playerDict[self.hitter].Hit(5, playerDict[self.hitter].vel[0], 1, playerDict[self.hitter]) # hitter

        self.collide(map, current_rect)
        

    def collide(self, map, rect):
        # colliding is false unless player is touching a block(for screenshaking)
        self.colliding = False
        for item in map:
            if rect.colliderect(item):
                if self.vel[1] > 1:
                    self.vel[1] = 0
                    self.pos[1] = item.top - 31
                    self.colliding = True
                    if self.jump:
                        self.vel[1] -= 25
                        self.pos[1] -= 1
    

    def dash(self):
        if self.Dash and self.cooldown == 0 and self.dashCount <= 0:
            self.dashCount = 20

        if self.dashCount > 0:
            self.dashCount -= 1
            if self.facing == 1:
                self.vel[0] = -37
            elif self.facing == 0:
                self.vel[0]= 37

            if self.dashCount == 0:
                self.cooldown = 10

        if self.Dash and self.cooldown > 0:
            self.vel[0] = 0
            if self.moving:
                if self.facing == 1:
                    self.vel[0] = -10
                else:
                    self.vel[0] = 10

        if self.cooldown > 0:
            self.cooldown -= 1
            self.Dash = False
        
    
    def Hit(self, intial, current, facing, hitter):
        #v(t) = velocity at time, v_0 = intial velocity, e base log, k = decay constant
        decay = 0.1
        if abs(current) <= 1:
            self.hit = False
            hitter.vel[0] = 0            
            print("normal")
            return 0
        elif abs(current) > 0 and facing == 1:
            current = intial * math.e**(-decay * self.t)
            return -current
        elif abs(current) > 0 and facing == 0:
            current = intial * math.e**(-decay * self.t)
            return current

    def __repr__(self):
        return str(self.pos) + "," + str(self.color) + "," + str(self.id)
        