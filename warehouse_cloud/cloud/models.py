from django.db import models

RED = 'R'
WHITE = 'W'
YELLOW = 'Y'
item_type_choices = [
    (RED, 'Red'),
    (WHITE, 'White'),
    (YELLOW, 'Yellow'),
]


class Inventory(models.Model):
    item_type = models.CharField(max_length=1, choices=item_type_choices)
    value = models.IntegerField()
    updated = models.DateTimeField()


class Order(models.Model):
    order_made = models.DateTimeField()
    order_completed = models.DateTimeField()
    item_type = models.CharField(max_length=1, choices=item_type_choices)

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
    order_status = models.IntegerField(choices=order_status_choices)


class Sensory(models.Model):
    sensorID = models.CharField(max_length=50)
    value = models.FloatField()
    datetime = models.DateTimeField()
