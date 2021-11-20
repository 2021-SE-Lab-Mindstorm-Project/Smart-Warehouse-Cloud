from . import rl
from .models import Inventory, Order


class Warehouse:
    def __init__(self, anomaly_aware):
        # config
        self.total_orders = 20
        self.cap_conveyor = 5
        self.cap_wait = 5
        self.reward_order = 25
        self.reward_trash = 100
        self.reward_wait = 1
        self.anomaly_duration = 10

        self.tick = 0
        self.anomaly_aware = anomaly_aware
        self.rl_model = rl.DQN(anomaly_aware, path='../model/a_rl.pth' if self.anomaly_aware else '../model/rl.pth')

        self.c = [0] * 4

        self.c_waiting = 0
        self.c_allow = 3
        self.r_allow = [False] * 3
        self.s_allow = False

        self.r_wait = [0] * 3
        self.s_wait = 0

        self.count = [0] * 3
        self.current_anomaly = [-1] * 3

        self.reward = 0
        self.old_state = None
        self.old_decision = None
        self.old_reward = 0

    def need_decision(self):
        if sum(self.c) == 0:
            return False

        num_true = 0
        for ans in self.available():
            if ans:
                num_true += 1

        return num_true > 1

    def available(self, i=None):
        if i is not None:
            inventory_objects = Inventory.objects.filter(stored=i)
            ans = len(inventory_objects) < self.cap_conveyor
            if not self.anomaly_aware:
                return ans
            return ans and self.current_anomaly[i] == -1

        ans = []
        for i in range(3):
            inventory_objects = Inventory.objects.filter(stored=i)
            single_ans = len(inventory_objects) < self.cap_conveyor
            if not self.anomaly_aware:
                ans.append(single_ans)
            else:
                ans.append(single_ans and self.current_anomaly[i] == -1)
        return ans

    def get_available(self):
        available = self.available()
        ans = []
        for i, avail in enumerate(available):
            if avail:
                ans.append(i)
        return ans

    def get_inventory(self, item):
        return self.c[item - 1] + len(Inventory.objects.filter(item_type=item))

    def get_order(self, is_sum=True):
        if is_sum:
            return len(Order.objects.all())

        orders = []
        for i in range(4):
            orders.append(len(Order.objects.filter(item_type=i + 1)))

        return orders

    def get_state(self):
        def repr_list(conveyor):
            ans = 0
            for i, item in enumerate(conveyor):
                ans += item.item_type * (5 ** (5 - i - 1))
            return ans

        ans = [self.tick]
        for i in range(4):
            ans.append(repr_list(Inventory.objects.filter(stored=i)))
        ans.extend(self.get_order(False))

        if self.anomaly_aware:
            anomaly_number = 0
            for i, anomaly in enumerate(self.current_anomaly):
                if anomaly != -1:
                    anomaly_number += (2 ** i)
            ans.append(anomaly_number)

        return ans
