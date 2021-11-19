# Generated by Django 3.2.8 on 2021-11-19 08:12

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Inventory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_type', models.IntegerField(choices=[(1, 'Red'), (2, 'White'), (3, 'Yellow'), (4, 'Blue')])),
                ('stored', models.IntegerField(choices=[(0, 'Left'), (1, 'Middle'), (2, 'Right'), (3, 'Shipment'), (4, 'Stuck')])),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sender', models.IntegerField(choices=[(0, 'User'), (1, 'Cloud'), (11, '[Edge] Classification'), (12, '[Edge] Repository'), (13, '[Edge] Shipment'), (21, '[Machine] Classification'), (22, '[Machine] Repository-1'), (23, '[Machine] Repository-2'), (24, '[Machine] Repository-3'), (25, '[Machine] Shipment')])),
                ('title', models.CharField(default='', max_length=50)),
                ('msg', models.TextField(blank=True, default='', null=True)),
                ('datetime', models.DateTimeField(default=datetime.datetime.now)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('made', models.DateTimeField(default=datetime.datetime.now)),
                ('completed', models.DateTimeField(blank=True, null=True)),
                ('item_type', models.IntegerField(choices=[(1, 'Red'), (2, 'White'), (3, 'Yellow'), (4, 'Blue')])),
                ('dest', models.IntegerField(choices=[(0, 'Left'), (1, 'Middle'), (2, 'Right'), (3, 'Shipment'), (4, 'Stuck')])),
                ('status', models.IntegerField(choices=[(1, 'Order Received'), (2, 'Repository Processing'), (3, 'Shipment Processing'), (4, 'Order Completed')], default=1)),
            ],
        ),
        migrations.CreateModel(
            name='Sensory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sensorID', models.CharField(max_length=50)),
                ('value', models.FloatField()),
                ('datetime', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='Status',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.BooleanField(default=False)),
                ('experiment_type', models.TextField(default='')),
                ('dm_type', models.TextField(default='')),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Verification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('property_name', models.TextField(default='')),
                ('verification_result', models.BooleanField(default=True)),
                ('verified', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
