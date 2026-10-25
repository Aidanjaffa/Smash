import gymnasium as gym
from gymnasium import spaces
import numpy as np
import 

class EdgeBrawlersEnv(gym.Env):

    metadata = {"render_modes": ["human"]}

    def __init__(self):
        super.__init__()

        # [left, right, jump, dash, down attack]
        self.action_space = spaces.discrete(5)

        # [self.x, self.y, enemy.x, enemy.y, lives]
        self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(5,), dtype=np.float32)
    
    def step(self, action):
        if action == 0:


