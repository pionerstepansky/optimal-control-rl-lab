import numpy as np
import torch
from numpy.linalg import norm


class EarthOrbitalMotion:
    def __init__(self, action_radius=np.array([0.5, 0.5]),
                 initial_state=np.array([0, 6900, 0, 0, 0.001109]),
                 normalized_vector=np.array([1 / 2000, 1 / 7000, 100, 1, 100]),
                 terminal_time=2000, dt=100, inner_step_n=100, required_orbit=6900):

        self.state_dim = 5
        self.action_dim = 2
        self.action_radius = action_radius
        self.action_min = - self.action_radius
        self.action_max = + self.action_radius

        self.load_constants()
        self.required_orbit = np.array([required_orbit, np.sqrt(self.G * self.M / required_orbit ** 3)])

        self.initial_state = initial_state
        self.initial_state[4] = np.sqrt(
            self.G * self.M / ((initial_state[1]) ** 3))  # уточнение орбитальной скорости вращения вокруг Земли
        self.terminal_time = terminal_time
        self.dt = dt
        self.r = 0.001
        self.beta = self.r
        self.inner_step_n = inner_step_n
        self.inner_dt = self.dt / self.inner_step_n
        self.normalized_vector = normalized_vector  # вектор масштабирования координат состояния
        self.state = self.reset()

    def load_constants(self):
        '''
        Постоянные для движения по околоземной орбите
        '''
        self.M = 5.9726e24  # масса Земли, кг
        self.m = 50  # масса спутника, кг
        self.R = 6371  # радиус Земли, км
        self.G = 6.67448478e-20  # гравитационная постоянная, км^3/(кг*c^2)

    def f(self, state, u):
        state_update = np.ones(self.state_dim)
        state_update[1] = state[2]
        state_update[2] = state[1] * state[4] ** 2 - self.G * self.M / (state[1] ** 2) + u[0] / (1000 * self.m)
        state_update[3] = state[4]
        state_update[4] = -2 * state[4] * state[2] / state[1] + u[1] / (state[1] * self.m * 1000)

        return state_update

    def g(self, state):
        shape = state.shape

        t, x0, y0, x, y = state
        nv = self.normalized_vector
        x0_grad = torch.zeros((shape[1], 2)).transpose(0, 1)
        x_grad = torch.tensor([nv[2] / (1000 * self.m), 0]).repeat(shape[1], 1).transpose(0, 1)
        y0_grad = torch.zeros((shape[1], 2)).transpose(0, 1)
        y_grad = torch.column_stack([torch.zeros(x0.shape), nv[1] * nv[4] / (x0 * self.m * 1000)]).transpose(0, 1)

        value = torch.stack([x0_grad, y0_grad, x_grad, y_grad]).transpose(0, 2).type(torch.FloatTensor)
        return value

    def reset(self):
        self.state = self.initial_state * self.normalized_vector
        return self.state

    def step(self, action):
        self.state = self.state / self.normalized_vector
        for _ in range(self.inner_step_n):
            # self.state = self.state + self.f(self.state, action) * self.inner_dt
            k1 = self.f(self.state, action)
            k2 = self.f(self.state + k1 * self.inner_dt / 2, action)
            k3 = self.f(self.state + k2 * self.inner_dt / 2, action)
            k4 = self.f(self.state + k3 * self.inner_dt, action)
            self.state = self.state + (k1 + 2 * k2 + 2 * k3 + k4) * self.inner_dt / 6

        if self.state[0] >= self.terminal_time:
            reward = -norm([self.required_orbit[0] - self.state[1], 100000 * (self.required_orbit[1] - self.state[4])])
            done = True
        else:
            reward = -self.r * norm(action) * self.dt
            done = False

        self.state = self.state * self.normalized_vector
        return self.state, reward, done, None

    def get_state_obs(self):
        return 'time: %.3f  x: %.3f delta_x y: %.3f delta_y: %.3f' % (self.state[0], self.state[1], self.state[2], self.state[3])
