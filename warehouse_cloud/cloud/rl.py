import math
import random
from collections import deque, namedtuple

import torch
from torch import nn, optim

Transition = namedtuple('Transition', ('state', 'tactic', 'reward', 'next_state'))
cuda_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

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
    def __init__(self, anomaly_aware, path=''):
        super(DQN, self).__init__()
        self.anomaly_aware = anomaly_aware
        self.input_size = 10 if anomaly_aware else 9
        self.output_size = 3
        self.hidden_size = 512

        self.model = nn.Sequential(
            nn.Linear(self.input_size, self.hidden_size),
            nn.ReLU(),
            nn.Linear(self.hidden_size, self.hidden_size),
            nn.ReLU(),
            nn.Linear(self.hidden_size, self.output_size)
        )

        self.steps = -1
        self.memory = Memory()
        self.optimizer = optim.RMSprop(self.parameters())

        if path != '':
            self.load_state_dict(torch.load(path, map_location=cuda_device))
            self.eval()

    def select_tactic(self, state, available):
        state_tensor = torch.FloatTensor([state]).to(cuda_device)

        result = self.model(state_tensor).view(self.output_size)
        result_sort = result.sort(descending=True)

        for i in range(self.output_size):
            selected = result_sort.indices[i]
            if available[selected]:
                return torch.LongTensor([[selected]]).to(cuda_device)

    def select_train_tactic(self, state, available):
        sample = random.random()
        eps_threshold = 0.05 + 0.85 * math.exp(-1. * self.steps / 200)
        self.steps += 1

        if sample > eps_threshold:
            with torch.no_grad():
                return self.select_tactic(state, available)

        candidate = []
        for i in range(len(available)):
            if available[i]:
                candidate.append(i)
        return torch.LongTensor([[random.choice(candidate)]]).to(cuda_device)

    def optimize_model(self):
        if len(self.memory) < 128:
            return

        transitions = self.memory.sample(128)
        batch = Transition(*zip(*transitions))

        next_state_batch = torch.cat(batch.next_state)
        state_batch = torch.cat(batch.state)
        tactic_batch = torch.cat(batch.tactic)
        reward_batch = torch.cat(batch.reward)

        selected_tactics = self.model(state_batch).gather(1, tactic_batch)
        next_state_values = self.model(next_state_batch).min(1)[0].detach()
        expected_values = (next_state_values * 0.99) + reward_batch

        criterion = nn.SmoothL1Loss()
        loss = criterion(selected_tactics, expected_values.unsqueeze(1))

        self.optimizer.zero_grad()
        loss.backward()
        for param in self.parameters():
            param.grad.data.clamp_(-1, 1)
        self.optimizer.step()

    def push_optimize(self, state, tactic_tensor, reward, next_state):
        self.memory.push(torch.FloatTensor([state]).to(cuda_device), tactic_tensor,
                         torch.FloatTensor([reward]).to(cuda_device),
                         torch.FloatTensor([next_state]).to(cuda_device))
        self.optimize_model()
