import gymnasium as gym
from gymnasium import spaces
import numpy as np
from objs.AIPlayer import Player
from objs.map import map
from objs.Camera import Camera
from helpers.config import *
import random

class EdgeBrawlersEnv(gym.Env):

    metadata = {"render_modes": ["human"]}

    def __init__(self, render_mode = None):
        super(EdgeBrawlersEnv, self).__init__()

        self.render_mode = render_mode
        if self.render_mode == "human":
            pygame.init()

            self.clock = pygame.time.Clock()
            self.clock.tick(gameSpeed)

        # [left, right, jump, dash, down attack]
        self.action_space = spaces.Discrete(5)

        # [self.x, self.y, enemy.x, enemy.y, lives]
        self.observation_space = spaces.Box(
            low=np.array([0, 0, 0, 0, 0], dtype=np.float32),
            high=np.array([1600, 1200, 3, 1600, 1200], dtype=np.float32)
            )

        self.camera = Camera()
        self.camera.scroll = [200, 100]
        self.playerDict = { 0 : Player([300, 0]), 1 : Player([400, 0])}
        self.map = map()

        self.time_alive = 0

    def step(self, action):
        reward = 0
        done = False

        # Actions
        if action == 0:
            self.playerDict[0].vel[0] = 7
            self.playerDict[0].facing = 0
        elif action == 1:
            self.playerDict[0].vel[0] = -7
            self.playerDict[0].facing = 1
        elif action == 2:
            self.playerDict[0].dash = True
        elif action == 3 and not self.playerDict[0].Jump:
            self.playerDict[0].Jump = True
            reward -= 5

        if action == 4 and self.playerDict[0].Jump:
            self.playerDict[0].down_attack = True

        # Player death
        if self.playerDict[0].pos[1] > 1500:
            reward -= 100
            self.playerDict[0].lives -= 1
            done = True

        # Enemy hit
        if self.playerDict[1].hit:
            reward += 80

        # Enemy death
        if self.playerDict[1].pos[1] > 1500:
            reward += 500
            done = True

        observation = self.get_observation()
        info = {}

        return observation, reward, done, False, info

        
    def get_observation(self):
        self.playerDict[0].Update(0, self.camera.scroll, surf, self.playerDict, self.map.rects, {})
        self.playerDict[1].Update(1, self.camera.scroll, surf, self.playerDict, self.map.rects, {})
        print(self.playerDict[0].pos)

        
        return np.array([self.playerDict[0].pos[0] + self.camera.scroll[0], self.playerDict[0].pos[1] + self.camera.scroll[1], 
                         self.playerDict[0].lives, 
                         self.playerDict[1].pos[0] + self.camera.scroll[0], self.playerDict[1].pos[1] + self.camera.scroll[1]], dtype=np.float32)

    def render(self, mode="human"):
        screen.fill((50, 50, 50))
        screen.blit(surf, (0, 0))
        surf.fill((0, 0, 0, 0))
        self.map.Draw(screen, self.camera.scroll)
        
        pygame.display.flip()
    
    def reset(self, *, seed = None, options = None):
        self.playerDict = { 0 : Player([random.randint(0, 800), 0]), 1 : Player([400, 0])}
        observation = self.get_observation()
        return observation, {}
    
    def close(self):
        pygame.quit


