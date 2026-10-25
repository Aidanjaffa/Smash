import pygame
import random
from helpers.config import *

class Player():
    def __init__(self, pos, id):
        self.pos = pygame.Vector2(pos)
        self.render_pos = pygame.Vector2(pos)
        self.vel = [0, 0]
        self.id = id
        self.color = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
        self.tint = None
        self.dashCount = 0

        # Mirror of server-side physics state used by predict()
        self.colliding = False
        self.jump = False
        self.moving = False
        self.Dash = False
        self.cooldown = 0

        self.man = pygame.transform.scale(pygame.image.load("assets/horatioStand.png").convert_alpha(), (10 * 2, 16 * 2))
        
        self.sprites = [self.man, pygame.transform.flip(self.man, True, False)]
        self.sword = pygame.transform.scale(pygame.image.load("assets/sword.png").convert_alpha(), (16 * 2, 10 * 2))
        self.swordL = pygame.transform.flip(self.sword, True, False)

        self.swordAngle = 16
        self.sword = pygame.transform.rotate(self.sword, self.swordAngle)
        self.swordL = pygame.transform.rotate(self.swordL, self.swordAngle)
        self.swordD = pygame.transform.rotate(self.swordL, 90)

        self.down_attack = False

        self.facing = 0
        self.afterImages = []
        pass

    def apply_input(self, data):
        # Mirror server.py @sio.on("input"): zero vel, set based on which key is held
        left = data.get("left", False)
        right = data.get("right", False)
        self.vel[0] = 0
        self.moving = False
        if left:
            self.vel[0] = -15
            self.moving = True
            self.facing = 1
        elif right:
            self.vel[0] = 15
            self.moving = True
            self.facing = 0

    def predict(self, map_rects):
        # Mirror of server_objs/Player.py update() for walk + gravity + jump + ground collision.
        # Dash/hit are server-authoritative and resolved via reconcile().
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]

        current_rect = pygame.Rect(self.pos[0], self.pos[1], 10 * 2, 16 * 2)

        if not self.colliding:
            self.vel[1] += 3
        if self.vel[1] > 50:
            self.vel[1] = 50

        self.colliding = False
        for item in map_rects:
            if current_rect.colliderect(item):
                if self.vel[1] > 1:
                    self.vel[1] = 0
                    self.pos[1] = item.top - 31
                    self.colliding = True
                    if self.jump:
                        self.vel[1] -= 25
                        self.pos[1] -= 1

    def dash_predict(self):
        # Mirror of server_objs/Player.py dash(). Dash press is predicted locally to
        # avoid the round-trip snap; the server still runs the same logic in lockstep.
        if self.Dash and self.cooldown == 0 and self.dashCount <= 0:
            self.dashCount = 20

        if self.dashCount > 0:
            self.dashCount -= 1
            if self.facing == 1:
                self.vel[0] = -37
            elif self.facing == 0:
                self.vel[0] = 37

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

    def reconcile(self, server_state, pending_inputs, map_rects):
        # Server-authoritative prediction with input replay:
        #   1. Drop the inputs the server has already processed (seq <= ack).
        #   2. Snap to the server's authoritative state.
        #   3. Replay every still-unacked input on top of it.
        # The rendered position is therefore always the server's truth fast-
        # forwarded by our own pending inputs, so it stays responsive yet can
        # never silently drift until it teleports.
        ack = server_state.get("last_ack", 0)
        while pending_inputs and pending_inputs[0]["seq"] <= ack:
            pending_inputs.popleft()

        self.pos = pygame.Vector2(server_state["pos"])
        self.vel = list(server_state.get("vel", [0, 0]))

        # During knockback the server owns vel[0] entirely (see server Hit()),
        # so follow it exactly instead of predicting over it.
        if server_state.get("hit", False):
            return

        self.colliding = server_state.get("colliding", False)
        self.cooldown = server_state.get("cooldown", 0)
        self.dashCount = server_state.get("dashCount", 0)
        self.facing = server_state.get("facing", self.facing)

        for inp in pending_inputs:
            self.apply_input(inp)
            self.jump = inp["jump"]
            if inp["dash"]:
                self.Dash = True
            self.predict(map_rects)
            self.dash_predict()

    def draw(self, screen, scroll, use_local=None):
        self.tint = self.applyTints(screen, scroll)
        self.dash(scroll, screen)

        
        if not self.down_attack:
            if self.facing == 0:
                screen.blit(self.sword, (self.render_pos[0] + 10 + scroll[0], self.render_pos[1] + 5 + scroll[1]))
            elif self.facing == 1:
                screen.blit(self.swordL, (self.render_pos[0] - 30 + scroll[0], self.render_pos[1] + 5 + scroll[1]))
        else:
            screen.blit(self.swordD, (self.render_pos[0] + scroll[0], self.render_pos[1] + 15 + scroll[1]))
    

    def applyTints(self, surf, scroll):
        tint = pygame.Surface((10 * 2, 16 * 2), pygame.SRCALPHA)
        tint.fill((self.color[0], self.color[1], self.color[2], 255))
        surf.blit(self.sprites[self.facing], (self.render_pos[0] + scroll[0], self.render_pos[1] + scroll[1]))
        
        surf.blit(tint, (self.render_pos[0] + scroll[0], self.render_pos[1] + scroll[1]),
                    special_flags=pygame.BLEND_RGBA_MULT)
        
        if self.dashCount > 0:
            self.afterImages.append([self.render_pos[0], self.render_pos[1], 255])
        
        return tint
    

    def dash(self, scroll, surf):

        # if len(self.afterImages) > 10:
        #     self.afterImages.pop(0)
        if len(self.afterImages) > 0:
            self.AfterImage(surf, self.tint, scroll)

        # Fading by setting the alpha
        if len(self.afterImages) == 0:
            self.sprites[self.facing].set_alpha(255)
        


    def AfterImage(self, surf, sprite, scroll):
        for sprite in self.afterImages:
            surf.blit(self.sprites[self.facing], (sprite[0] + scroll[0], sprite[1] + scroll[1])) # main guy
            surf.blit(self.tint, (sprite[0] + scroll[0], sprite[1] + scroll[1]), special_flags=pygame.BLEND_RGBA_MULT) # tint
            self.tint.set_alpha(sprite[2])
            sprite[2] -= 10
            if sprite[2] <= 0:
                self.afterImages.remove(sprite)
        