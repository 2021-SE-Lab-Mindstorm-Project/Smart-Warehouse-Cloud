import random
from collections import namedtuple, deque

import torch
from torch import nn, optim

Transition = namedtuple('Transition', ('state', 'tactic', 'reward', 'next_state'))
batch_size = 128
gamma = 0.999


class Memory(object):
    def __init__(self):
        self.memory = deque(maxlen=10000)

    def push(self, *args):
        self.memory.append(Transition(*args))

    def sample(self, batch_size):
        return random.sample(self.memory, batch_size)

    def __len__(self):
        return len(self.memory)


class DQN(nn.Module):
    def __init__(self, input_size, path=''):
        super(DQN, self).__init__()
        self.input_size = input_size

        self.model = nn.Sequential(
            nn.Linear(self.input_size, 512),
            nn.ReLU(),
            nn.Linear(512, 512),
            nn.ReLU(),
            nn.Linear(512, 4)
        )

        self.memory = Memory()
        self.optimizer = optim.RMSprop(self.parameters())

        if path != '':
            self.load_state_dict(torch.load(path, map_location=torch.device("cpu")))
            self.eval()

    def select_tactic(self, state, available):
        state_tensor = torch.FloatTensor([state]).to(torch.device("cpu"))
        result = self.model(state_tensor).sort()
        for i in range(4):
            if int(result.indices[0][i]) == 3 or available[int(result.indices[0][i])]:
                return result.indices[0][i]

    def optimize_model(self):
        if len(self.memory) < batch_size:
            return

        transitions = self.memory.sample(batch_size)
        batch = Transition(*zip(*transitions))

        non_final_mask = torch.tensor(tuple(map(lambda s: s is not None, batch.next_state)), dtype=torch.bool)
        non_final_next_states = torch.cat([s for s in batch.next_state if s is not None])
        state_batch = torch.cat(batch.state)
        tactic_batch = torch.cat(batch.tactic)
        reward_batch = torch.cat(batch.reward)

        selected_tactics = self.model(state_batch).gather(1, tactic_batch)
        next_state_values = torch.zeros(batch_size)
        next_state_values[non_final_mask] = self.model(non_final_next_states).max(1)[0].detach()
        expected_values = (next_state_values * gamma) + reward_batch

        criterion = nn.SmoothL1Loss()
        loss = criterion(selected_tactics, expected_values.unsqueeze(1))

        self.optimizer.zero_grad()
        loss.backward()
        for param in self.parameters():
            param.grad.data.clamp_(-1, 1)
        self.optimizer.step()

    def push_optimize(self, state, tactic_tensor, reward, next_state):
        if next_state is None:
            self.memory.push(torch.FloatTensor([state]), tactic_tensor, torch.FloatTensor([reward]), None)
        else:
            self.memory.push(torch.FloatTensor([state]), tactic_tensor, torch.FloatTensor([reward]),
                             torch.FloatTensor([next_state]))

        self.optimize_model()
