import datetime

from django.db import models

RED = 1
WHITE = 2
YELLOW = 3
BLUE = 4
item_type_choices = [
    (RED, 'Red'),
    (WHITE, 'White'),
    (YELLOW, 'Yellow'),
    (BLUE, 'Blue')
]

LEFT = 0
MIDDLE = 1
RIGHT = 2
SHIPMENT = 3
dest_choices = [
    (LEFT, 'Left'),
    (MIDDLE, 'Middle'),
    (RIGHT, 'Right'),
    (SHIPMENT, 'Shipment')
]


class Inventory(models.Model):
    item_type = models.IntegerField(choices=item_type_choices)
    stored = models.IntegerField(choices=dest_choices)
    updated = models.DateTimeField(auto_now=datetime.datetime.now)


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


USER = 0
CLOUD = 1
EDGE_CLASSIFICATION = 11
EDGE_REPOSITORY = 12
EDGE_SHIPMENT = 13
MACHINE_CLASSIFICATION = 21
MACHINE_REPOSITORY_1 = 22
MACHINE_REPOSITORY_2 = 23
MACHINE_REPOSITORY_3 = 24
MACHINE_SHIPMENT = 25

sender_choices = [
    (USER, 'User'),
    (CLOUD, 'Cloud'),
    (EDGE_CLASSIFICATION, '[Edge] Classification'),
    (EDGE_REPOSITORY, '[Edge] Repository'),
    (EDGE_SHIPMENT, '[Edge] Shipment'),
    (MACHINE_CLASSIFICATION, '[Machine] Classification'),
    (MACHINE_REPOSITORY_1, '[Machine] Repository-1'),
    (MACHINE_REPOSITORY_2, '[Machine] Repository-2'),
    (MACHINE_REPOSITORY_3, '[Machine] Repository-3'),
    (MACHINE_SHIPMENT, '[Machine] Shipment')
]


class Message(models.Model):
    sender = models.IntegerField(choices=sender_choices)
    title = models.CharField(default='', max_length=50)
    msg = models.TextField(default='', blank=True, null=True)
    datetime = models.DateTimeField(default=datetime.datetime.now)


class Status(models.Model):
    status = models.BooleanField(default=False)
    updated = models.DateTimeField(auto_now=datetime.datetime.now)


class Verification(models.Model):
    property_name = models.TextField(default='')
    verification_result = models.BooleanField(default=True)
    verified = models.DateTimeField(auto_now=datetime.datetime.now)
