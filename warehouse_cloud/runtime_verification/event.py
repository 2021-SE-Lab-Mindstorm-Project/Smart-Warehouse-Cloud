from cloud.models import Inventory


class Event:
    def __init__(self, name):
        self.name = name

    def check_hold(self):
        return False

class InventoryOverEvent(Event):
    def check_hold(self):
        for i in range(4):
            items = Inventory.objects.filter(stored=i)
            if len(items) > 5:
                return True

        return False

class ItemTypeValidEvent(Event):
    def check_hold(self):
        items = Inventory.objects.filter(stored__lt=4)
        for item in items:
            if item.item_type not in [1, 2, 3, 4]:
                return False

        return True

class ItemNumberEvent(Event):
    def __init__(self, name, x):
        super().__init__(name)
        self.name = name
        self.limit = x
        self.past = False

    def check_hold(self):
        items = Inventory.objects.filter(stored__lt=4)
        if len(items) >= self.limit:
            return True

        return False or self.past
