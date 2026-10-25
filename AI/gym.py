import gymnasium as gym
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from tqdm import tqdm
import dill as pickle


class Player():
    def __init__(self,
                 env: gym.Env, # training evrion
                 learning_rate, 
                 initial_epsilon, # epsilon means in ML likelyhood to explore (ε) vs exploit (1-ε)
                 epsilon_decay, # need to gradually reduce so the ai stops exploring and starts exploiting
                 final_epsilon, # should decay to and stop
                 discount_factor=0.95): # also known as gamma closer to 1 = future rewards priority 0 = immideate 
        
        self.env = env
        self.q_values = defaultdict(lambda: np.zeros(env.action_space.n)) # q values represent expected future rewards for an action

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
        self.epsilon = max(self.final, self.epsilon - self.epsilon_decay) # chooses the bigger epsilon values

    def truncateVector(self, obs):
        return tuple(np.round(obs, 2)) # number is the decimal points to truncate to


# Training loop
num_episodes = 10000
env = gym.make("CartPole-v1")
env = gym.wrappers.RecordEpisodeStatistics(env, buffer_length=num_episodes)

agent = Player(
    env=env,
    learning_rate=0.01,
    initial_epsilon=1.0,
    epsilon_decay=1 / (num_episodes / 2),
    final_epsilon=0.1,
    discount_factor=0.95
)

for episode in tqdm(range(num_episodes)):
    obs, info = env.reset()
    done = False

    while not done:
        action = agent.get_action(obs)
        next_obs, reward, terminated, truncated, info = env.step(action)

        agent.update(obs, action, reward, terminated, truncated, next_obs)

        done = terminated or truncated
        obs = next_obs

    agent.decay()

with open("q_table.pkl", "wb") as f:
    pickle.dump(agent.q_values, f)
    print("Q_Table Saved")

def get_moving_avgs(arr, window, convolution_mode):
    return np.convolve(
        np.array(arr).flatten(),
        np.ones(window),
        mode=convolution_mode
    ) / window

# Smooth over a 500 episode window
rolling_length = 800
fig, axs = plt.subplots(ncols=3, figsize=(12, 5))

axs[0].set_title("Episode rewards")
reward_moving_average = get_moving_avgs(
    env.return_queue,
    rolling_length,
    "valid"
)
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