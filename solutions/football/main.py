import math
import sys

import numpy as np
import torch

from kaggle_environments.envs.football.helpers import Action, GameMode
from torch import nn

sys.path.append('/kaggle_simulations/agent/')


class Seq_Network(nn.Module):
    def __init__(self, layers, hidden_activation, output_activation=None):
        super().__init__()
        hidden_layers = layers[:-1]
        network = [nn.Sequential(nn.Linear(i, o), hidden_activation) for i, o in
                   zip(hidden_layers, hidden_layers[1:])]
        network.append(nn.Linear(layers[-2], layers[-1]))
        if output_activation:
            network.append(output_activation)
        self.network = nn.Sequential(*network)
        self.apply(self._init_weights_)

    def forward(self, tensor):
        return self.network(tensor)

    def _init_weights_(self, m):
        if type(m) == nn.Linear:
            torch.nn.init.xavier_normal_(m.weight)
            m.bias.data.fill_(0.01)


action_model = Seq_Network([115, 80, 40, 19], nn.ReLU())
# action_model.load_state_dict(torch.load('/kaggle_simulations/agent/weights'))
action_model.load_state_dict(torch.load('./weights'))

# result = loaded_model.score(X_test, y_test)
# print(result)

directions = [[Action.TopLeft, Action.Top, Action.TopRight],
              [Action.Left, Action.Idle, Action.Right],
              [Action.BottomLeft, Action.Bottom, Action.BottomRight]]

# track raw data to troubleshoot...
track_raw_data = []

perfectRange = [[0.7, 0.95], [-0.12, 0.12]]


def inside(pos, area):
    return area[0][0] <= pos[0] <= area[0][1] and area[1][0] <= pos[1] <= area[1][1]


def get_distance(pos1, pos2):
    return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5


def get_heading(pos1, pos2):
    raw_head = math.atan2(pos1[0] - pos2[0], pos1[1] - pos2[1]) / math.pi * 180

    if raw_head < 0:
        head = 360 + raw_head
    else:
        head = raw_head
    return head


def get_action(action_num):
    if action_num == 0:
        return Action.Idle
    if action_num == 1:
        return Action.Left
    if action_num == 2:
        return Action.TopLeft
    if action_num == 3:
        return Action.Top
    if action_num == 4:
        return Action.TopRight
    if action_num == 5:
        return Action.Right
    if action_num == 6:
        return Action.BottomRight
    if action_num == 7:
        return Action.Bottom
    if action_num == 8:
        return Action.BottomLeft
    if action_num == 9:
        return Action.LongPass
    if action_num == 10:
        return Action.HighPass
    if action_num == 11:
        return Action.ShortPass
    if action_num == 12:
        return Action.Shot
    if action_num == 13:
        return Action.Sprint
    if action_num == 14:
        return Action.ReleaseDirection
    if action_num == 15:
        return Action.ReleaseSprint
    if action_num == 16:
        # return Action.Sliding
        return Action.Idle
    if action_num == 17:
        return Action.Dribble
    if action_num == 18:
        # return Action.ReleaseDribble
        return Action.Idle
    return Action.Right


def agent(obs):
    controlled_player_pos = obs['left_team'][obs['active']]
    x = controlled_player_pos[0]
    y = controlled_player_pos[1]
    pactive = obs['active']

    if obs["game_mode"] == GameMode.Penalty:
        return Action.Shot
    if obs["game_mode"] == GameMode.Corner:
        if controlled_player_pos[0] > 0:
            return Action.Shot
    if obs["game_mode"] == GameMode.FreeKick:
        return Action.Shot

    # Make sure player is running.
    if 0 < controlled_player_pos[0] < 0.6 and Action.Sprint not in obs['sticky_actions']:
        return Action.Sprint
    elif 0.6 < controlled_player_pos[0] and Action.Sprint in obs['sticky_actions']:
        return Action.ReleaseSprint

    # if we have the ball
    if obs['ball_owned_player'] == obs['active'] and obs['ball_owned_team'] == 0:
        dat = []
        to_append = []
        # return Action.Right
        # get controller player pos
        controlled_player_pos = obs['left_team'][obs['active']]

        if inside(controlled_player_pos, perfectRange) and controlled_player_pos[0] < obs['ball'][0]:
            return Action.Shot

        goalx = 0.0
        goaly = 0.0

        sidelinex = 0.0
        sideliney = 0.42

        goal_dist = get_distance((x, y), (goalx, goaly))
        sideline_dist = get_distance((x, y), (sidelinex, sideliney))
        to_append.append(goal_dist)
        to_append.append(sideline_dist)

        for i in range(len(obs['left_team'])):
            dist = get_distance((x, y), (obs['left_team'][i][0], obs['left_team'][i][1]))
            head = get_heading((x, y), (obs['left_team'][i][0], obs['left_team'][i][1]))
            to_append.append(dist)
            to_append.append(head)

        for i in range(len(obs['right_team'])):
            dist = get_distance((x, y), (obs['right_team'][i][0], obs['right_team'][i][1]))
            head = get_heading((x, y), (obs['right_team'][i][0], obs['right_team'][i][1]))
            to_append.append(dist)
            to_append.append(head)

        dat.append(to_append)

        print(dat)
        predicted = action_model.predict(dat)

        do = get_action(predicted)

        if do is None:
            return Action.Right
        else:
            return do

    # if we don't have ball run to ball
    else:
        dirsign = lambda x: 1 if abs(x) < 0.01 else (0 if x < 0 else 2)
        # where ball is going
        ball_targetx = obs['ball'][0] + (obs['ball_direction'][0] * 5)
        ball_targety = obs['ball'][1] + (obs['ball_direction'][1] * 5)

        e_dist = get_distance(obs['left_team'][obs['active']], obs['ball'])

        if e_dist > .01:
            # Run where ball will be
            xdir = dirsign(ball_targetx - controlled_player_pos[0])
            ydir = dirsign(ball_targety - controlled_player_pos[1])
            return directions[ydir][xdir]
        else:
            # Run towards the ball.
            xdir = dirsign(obs['ball'][0] - controlled_player_pos[0])
            ydir = dirsign(obs['ball'][1] - controlled_player_pos[1])
            return directions[ydir][xdir]
