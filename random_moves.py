import random
from wrapper import EdgeBrawlersEnv
env = EdgeBrawlersEnv()

for episode in range(5):
    obs = env.reset()
    done = False
    
    while not done:
        action = env.action_space.sample()  # Random action
        obs, reward, done, _, _ = env.step(action)
        env.render()  # Show the game

env.close()