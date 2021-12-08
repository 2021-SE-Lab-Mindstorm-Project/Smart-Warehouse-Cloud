from cloud.models import Inventory


class Event:
    def __init__(self, name):
        self.name = name

    def check_hold(self):
        return False

class InventoryOverEvent(Event):
    def __init__(self):
        super().__init__("The number of items is over the capacity")

    def check_hold(self):
        for i in range(4):
            items = Inventory.objects.filter(stored=i)
            if len(items) > 5:
                return True

        return False

class ItemTypeValidEvent(Event):
    def __init__(self):
        super().__init__("Items entering the system are one of red, white, yellow, blue")

    def check_hold(self):
        items = Inventory.objects.filter(stored__lt=4)
        for item in items:
            if item.item_type not in [1, 2, 3, 4]:
                return False

        return True

class ItemNumberEvent(Event):
    def __init__(self, x):
        super().__init__("Total number of items in the system reaches ”" + str(x))
        self.limit = x
        self.past = False

    def check_hold(self):
        items = Inventory.objects.filter(stored__lt=4)
        if len(items) >= self.limit:
            return True

        return False or self.past
