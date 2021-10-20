import datetime

from django.db import models

RED = 1
WHITE = 2
YELLOW = 3
item_type_choices = [
    (RED, 'Red'),
    (WHITE, 'White'),
    (YELLOW, 'Yellow'),
]

LEFT = 1
MIDDLE = 2
RIGHT = 3
dest_choices = [
    (LEFT, 'Left'),
    (MIDDLE, 'Middle'),
    (RIGHT, 'Right')

]


class Inventory(models.Model):
    item_type = models.IntegerField(choices=item_type_choices)
    value = models.IntegerField()
    updated = models.DateTimeField()


class Order(models.Model):
    made = models.DateTimeField(default=datetime.datetime.now)
    completed = models.DateTimeField(null=True, blank=True)
    item_type = models.IntegerField(choices=item_type_choices)
    dest = models.IntegerField(choices=dest_choices)

    STATUS1 = 1
    STATUS2 = 2
    STATUS3 = 3
    STATUS4 = 4
    order_status_choices = [
        (STATUS1, 'Order Received'),
        (STATUS2, 'Repository Processing'),
        (STATUS3, 'Shipment Processing'),
        (STATUS4, 'Order Completed')
    ]
    status = models.IntegerField(choices=order_status_choices, default=1)


class Sensory(models.Model):
    sensorID = models.CharField(max_length=50)
    value = models.FloatField()
    datetime = models.DateTimeField()
