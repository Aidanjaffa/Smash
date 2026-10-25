import gymnasium as gym
import numpy as np
import dill as pickle

class Player():
    def __init__(self, q_table: dict, env: gym.Env):
        self.q_table = q_table
        self.env = env

    def get_action(self, obs):
        obs = self.truncateVector(obs)

        if obs not in self.q_table:
            return self.env.action_space.sample()
        return int(np.argmax(self.q_table[obs]))

    def truncateVector(self, obs):
        return tuple(np.round(obs, 2))
    

env = gym.make("CartPole-v1", render_mode="human")

with open("q_table.pkl", "rb") as file:
    table = pickle.load(file)

player = Player(table, env)
for games in range(1):
    observation, info = env.reset()

    over = False
    while not over:
        action = player.get_action(observation)
        next, reward, term, trunc, info = env.step(action)

        over = term or trunc

        observation = next
