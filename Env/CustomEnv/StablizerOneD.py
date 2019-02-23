

import gym
import numpy as np
import random
from copy import deepcopy
import matplotlib.pyplot as plt

class StablizerOneD(gym.Env):

    def __init__(self):
        super(StablizerOneD, self).__init__()

        self.stepCount = 0
        self.currentState = 0.0
        self.targetState = 0.0
        self.nbActions = 3
        self.stateDim = 1
        self.endStep = 200
    def step_count(self):
        return self.stepCount

    def step(self, action):
        self.stepCount += 1
        self.currentState += (random.random()-0.5)*0.4
        if action == 1: # move to positive
            self.currentState += 0.1
        if action == 2: # move to negative
            self.currentState -= 0.1

        if abs(self.currentState) < 1:
            reward = - abs(self.currentState)
            done = False
        else:
            reward = - abs(self.currentState) * (self.endStep - self.stepCount)
            done = True

        if self.stepCount > self.endStep:
            done = True


        return np.array([self.currentState]), reward, done, {}

    def reset(self):

        self.stepCount = 0
        self.currentState = (random.random() - 0.5)-0.1

        return np.array([self.currentState])


    def close(self):
        pass

    def seed(self):
        pass

    def render(self, mode='human'):
        pass

    def render_traj(self, stateSet, ax):
        ax.plot(np.array(stateSet)[:])

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
#the memo dict, where id-to-object correspondence is kept to reconstruct
#complex object graphs perfectly
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result



