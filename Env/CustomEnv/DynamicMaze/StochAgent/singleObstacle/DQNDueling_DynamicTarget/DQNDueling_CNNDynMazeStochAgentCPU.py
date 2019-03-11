

from Agents.DQN.DQN import DQNAgent
from Env.CustomEnv.DynamicMaze.DynamicMaze import DynamicMaze, TrajRecorder
from utils.netInit import xavier_init
from Agents.DQN.DQNA3C import DQNA3CMaster, SharedAdam
import json
from torch import optim
from copy import deepcopy
import numpy as np
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import math
import os

torch.manual_seed(1)
import torch.nn.functional as F
torch.set_num_threads(1)

configName = 'config.json'
with open(configName,'r') as f:
    config = json.load(f)
    
# Convolutional neural network (two convolutional layers)
class MulChanConvNet(nn.Module):
    def __init__(self, inputWidth, num_hidden, num_action):
        super(MulChanConvNet, self).__init__()
        
        self.inputShape = (inputWidth,inputWidth)
        self.layer1 = nn.Sequential( # input shape (1, inputWdith, inputWdith)
            nn.Conv2d(1,             # input channel
                      32,            # output channel
                      kernel_size=2, # filter size
                      stride=1,
                      padding=1),   # if want same width and length of this image after Conv2d, padding=(kernel_size-1)/2 if stride=1
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2)) # inputWdith / 2

        self.layer2 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=2, stride=1, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2)) # inputWdith / 2
        # add a fully connected layer
        #width = int(inputWidth / 4) + 1
        
        self.fc0 = nn.Linear(2, 32)
        self.fc1 = nn.Linear(self.featureSize() + 32, num_hidden)
#        self.fc2 = nn.Linear(num_hidden, num_action)

        dueling_size = 64
        # advantage layer
        self.advLayer1 = nn.Linear(num_hidden, dueling_size)
        self.advLayer2 = nn.Linear(dueling_size, num_action)

        # value layer
        self.valLayer1 = nn.Linear(num_hidden, dueling_size)
        self.valLayer2 = nn.Linear(dueling_size, 1)

        self.apply(xavier_init)

    def forward(self, state):
        x = state['sensor']
        y = state['target']
        xout = self.layer1(x)
        xout = self.layer2(xout)
        xout = xout.reshape(xout.size(0), -1)
        # mask xout for test
        # xout.fill_(0)
        yout = F.relu(self.fc0(y))
        out = torch.cat((xout, yout), 1)
        out = F.relu(self.fc1(out))

        adv = F.relu(self.advLayer1(out))
        adv = self.advLayer2(adv)

        val = F.relu(self.valLayer1(out))
        val = self.valLayer2(val)

        return val + adv - adv.mean()


    def featureSize(self):
        return self.layer2(self.layer1(torch.zeros(1, 1, *self.inputShape))).view(1, -1).size(1)


def plotPolicy(policy, nbActions):
    idx, idy = np.where(policy >=0)
    action = policy[idx,idy]
    plt.scatter(idx, idy, c = action, marker='s', s = 10)
    # for i in range(nbAction#s):
    #     idx, idy = np.where(policy == i)
    #     plt.plot(idx,idy, )



# directory = config['mazeFileName'].split('.')[0]
# if not os.path.exists(directory):
#     os.makedirs(directory)


def stateProcessor(state):
    # given a list a dictions like { 'sensor': np.array, 'target': np.array}
    # we want to get a diction like {'sensor': list of torch tensor, 'target': list of torch tensor}
    senorList = [item['sensor'] for item in state]
    targetList = [item['target'] for item in state]
    output = {'sensor': torch.tensor(senorList, dtype=torch.float32, device=config['device']),
              'target': torch.tensor(targetList, dtype=torch.float32, device=config['device'])}
    return output

env = DynamicMaze(config)

N_S = env.stateDim[0]
N_A = env.nbActions


policyNet = MulChanConvNet(N_S, 128, N_A)
targetNet = deepcopy(policyNet)
optimizer = optim.Adam(policyNet.parameters(), lr=config['learningRate'])


agent = DQNAgent(policyNet, targetNet, env, optimizer, torch.nn.MSELoss(reduction='none'), N_A,
                 stateProcessor=stateProcessor, config=config)



trainFlag = True
testFlag = True

if trainFlag:

    if config['loadExistingModel']:
        checkpoint = torch.load(config['saveModelFile'])
        agent.policyNet.load_state_dict(checkpoint['model_state_dict'])
        agent.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])


    plotPolicyFlag = True
    if plotPolicyFlag:

        for phiIdx in range(8):
            phi = phiIdx * np.pi/4.0
            policy = deepcopy(env.mapMat)
            for i in range(policy.shape[0]):
                  for j in range(policy.shape[1]):
                      if env.mapMat[i, j] == 1:
                          policy[i, j] = -1
                      else:
                          sensorInfo = env.agent.getSensorInfoFromPos(np.array([i, j, phi]))
                          distance = np.array(config['targetState']) - np.array([i, j])
                          dx = distance[0] * math.cos(phi) + distance[1] * math.sin(phi)
                          dy = distance[0] * math.sin(phi) - distance[1] * math.cos(phi)
                          state = {'sensor': sensorInfo, 'target': np.array([dx, dy])}
                          policy[i, j] = agent.getPolicy(state)
            np.savetxt('DynamicMazePolicyBeforeTrain' + config['mapName'] +'phiIdx'+ str(phiIdx) + '.txt', policy, fmt='%d', delimiter='\t')
    #
    # plotPolicy(policy, N_A)



    agent.train()


    if plotPolicyFlag:
        for phiIdx in range(8):
            phi = phiIdx * np.pi / 4.0
            policy = deepcopy(env.mapMat)
            for i in range(policy.shape[0]):
                for j in range(policy.shape[1]):
                    if env.mapMat[i, j] == 1:
                        policy[i, j] = -1
                    else:
                        sensorInfo = env.agent.getSensorInfoFromPos(np.array([i, j, phi]))
                        distance = np.array(config['targetState']) - np.array([i, j])
                        dx = distance[0] * math.cos(phi) + distance[1] * math.sin(phi)
                        dy = distance[0] * math.sin(phi) - distance[1] * math.cos(phi)
                        state = {'sensor': sensorInfo, 'target': np.array([dx, dy])}
                        policy[i, j] = agent.getPolicy(state)
            np.savetxt('DynamicMazePolicyAfterTrain' + config['mapName'] + 'phiIdx' + str(phiIdx) + '.txt', policy, fmt='%d',
                       delimiter='\t')

    torch.save({
                'model_state_dict': agent.policyNet.state_dict(),
                'optimizer_state_dict': agent.optimizer.state_dict(),
                }, config['saveModelFile'])


if testFlag:
    config['loadExistingModel'] = True

    if config['loadExistingModel']:
        checkpoint = torch.load(config['saveModelFile'])
        agent.policyNet.load_state_dict(checkpoint['model_state_dict'])
        agent.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

    recorder = TrajRecorder()
    agent.testPolicyNet(100, recorder)
    recorder.write_to_file(config['mapName'] + 'TestTraj.txt')

#plotPolicy(policy, N_A)
