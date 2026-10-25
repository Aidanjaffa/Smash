import gymnasium as gym
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from tqdm import tqdm
import dill as pickle
from wrapper import EdgeBrawlersEnv
import time


class Player():
    def __init__(self,
                 env: gym.Env, # training evrion
                 learning_rate, 
                 initial_epsilon, # epsilon means in ML likelyhood to explore (ε) vs exploit (1-ε)
                 epsilon_decay, # need to gradually reduce so the ai stops exploring and starts exploiting
                 final_epsilon, # should decay to and stop
                 discount_factor=0.95): # also known as gamma closer to 1 = future rewards priority 0 = immideate 
        
        self.env = env
        self.q_values = defaultdict(lambda: np.zeros(env.action_space.n) + 0.01) # q values represent expected future rewards for an action

        self.lr = learning_rate
        self.discount_factor = discount_factor

        self.epsilon = initial_epsilon
        self.epsilon_decay = epsilon_decay
        self.final = final_epsilon

        self.training_error = []

        pass

    def get_action(self, obs):
        # returns best action with probability 1 - ep
        # else random action
        obs = self.truncateVector(obs)
        if np.random.random() < self.epsilon:
            return self.env.action_space.sample()
        else:
            return int(np.argmax(self.q_values[obs]))
        # argmax returns the index of the highest number in the q_value dict and therfore chooses the action based on that val
    
    def update(self, obs, action, reward, term, trunc, next):
        # will update the q_value of an action 
        next = self.truncateVector(next)
        obs = self.truncateVector(obs)
        future_val = (not term) * np.max(self.q_values[next]) # next refers to the next observation which i assume means frame
        diff = reward + self.discount_factor * future_val - self.q_values[obs][action]
            # this gets the expected q val (from rewards and discount) and the current q val and then calcs the diff
            # reward + discounted future val - current

        self.q_values[obs][action] = self.q_values[obs][action] + self.lr * diff # updates val from current state action pair
        # aimes to improve q_vals over time by reducing the difference

        self.training_error.append(abs(diff))
    
    def decay(self):
        self.epsilon *= self.epsilon_decay
        self.epsilon = max(self.final, self.epsilon) # chooses the bigger epsilon values

    def truncateVector(self, obs):
            return (
        int(obs[0] // 50),
        int(obs[1] // 50),
        int(obs[2]),          # lives
        int(obs[3] // 50),
        int(obs[4] // 50)
    )

# Training loop
num_episodes = 2000
env = EdgeBrawlersEnv(render_mode=None)
env = gym.wrappers.RecordEpisodeStatistics(env, buffer_length=num_episodes)

agent = Player(
    env=env,
    learning_rate=0.1,
    initial_epsilon=1.0,
    epsilon_decay=0.995,
    final_epsilon=0.05,
    discount_factor=0.95
)

reward_moving_average = []
for episode in tqdm(range(num_episodes)):
    obs, info = env.reset()
    done = False
    timer = time.time() + 50
    episode_total = 0
    while not done:
        env.render()
        action = agent.get_action(obs)
        next_obs, reward, term, _, _ = env.step(action)

        agent.update(obs, action, reward, term, False, next_obs)

        done = term 
        obs = next_obs

        episode_total += reward

    reward_moving_average.append(episode_total)
    agent.decay()

def get_moving_avgs(arr, window, convolution_mode):
    return np.convolve(
        np.array(arr).flatten(),
        np.ones(window),
        mode=convolution_mode
    ) / window

# Smooth over a 500 episode window
rolling_length = 100
fig, axs = plt.subplots(ncols=3, figsize=(12, 5))

axs[0].set_title("Episode rewards")

axs[0].plot(range(len(reward_moving_average)), reward_moving_average)

axs[1].set_title("Episode lengths")
length_moving_average = get_moving_avgs(
    env.length_queue,
    rolling_length,
    "valid"
)
axs[1].plot(range(len(length_moving_average)), length_moving_average)

axs[2].set_title("Training Error")
training_error_moving_average = get_moving_avgs(
    agent.training_error,
    rolling_length,
    "same"
)
axs[2].plot(range(len(training_error_moving_average)), training_error_moving_average)
plt.tight_layout()
plt.show()