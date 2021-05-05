import numpy as np
import torch
import torch.nn as nn
import random
from collections import deque
from copy import deepcopy
from Agents.Utilities.LinearTransformations import transform_interval


class NAF:
    def __init__(self, state_dim, action_dim, action_min, action_max, q_model, noise,
                 batch_size=200, gamma=0.9999, tau=1e-3, q_model_lr=1e-4, learning_n_per_fit=1):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.action_max = action_max
        self.action_min = action_min

        self.q_model = q_model
        self.opt = torch.optim.Adam(self.q_model.parameters(), lr=q_model_lr)
        self.loss = nn.MSELoss()
        self.q_target = deepcopy(self.q_model)
        self.tau = tau
        self.memory = deque(maxlen=100000)
        self.gamma = gamma
        self.learning_n_per_fit = learning_n_per_fit

        self.batch_size = batch_size
        self.noise = noise

    def get_action(self, state):
        state = torch.FloatTensor(state)
        mu_value = self.q_model.mu_model(state).detach().numpy()
        noise = self.noise.noise()
        action = mu_value + noise
        action = transform_interval(action, self.action_min, self.action_max)
        return np.clip(action, self.action_min, self.action_max)

    def update_targets(self, target, original):
        for target_param, original_param in zip(target.parameters(), original.parameters()):
            target_param.data.copy_((1 - self.tau) * target_param.data + self.tau * original_param.data)

    def add_to_memory(self, sessions):
        for session in sessions:
            session_len = len(session['actions'])
            for i in range(session_len):
                self.memory.append([session['states'][i],
                                    session['actions'][i],
                                    session['rewards'][i],
                                    session['dones'][i],
                                    session['states'][i + 1]])

    def fit(self, sessions):
        self.add_to_memory(sessions)

        if len(self.memory) >= self.batch_size:
            for _ in range(self.learning_n_per_fit):
                batch = random.sample(self.memory, self.batch_size)
                states, actions, rewards, dones, next_states = map(torch.FloatTensor, zip(*batch))
                rewards = rewards.reshape(self.batch_size, 1)
                dones = dones.reshape(self.batch_size, 1)

                target = rewards + (1 - dones) * self.gamma * self.q_target.v_model(next_states).detach()
                loss = self.loss(self.q_model(states, actions), target)
                self.opt.zero_grad()
                loss.backward()
                self.opt.step()
                self.update_targets(self.q_target, self.q_model)