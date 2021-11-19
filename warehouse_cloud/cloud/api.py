import json
import random
from datetime import datetime, timedelta

import requests
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, viewsets
from rest_framework.response import Response

from warehouse_cloud.settings import settings
from . import models, rl
from .models import Sensory, Inventory, Order, Message, Status


# Serializer
class SensoryListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        sensory_data_list = [Sensory(**item) for item in validated_data]
        return Sensory.objects.bulk_create(sensory_data_list)


class SensorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensory
        fields = '__all__'
        list_serializer_class = SensoryListSerializer


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'


# Sensory Data
class SensoryViewSet(viewsets.ModelViewSet):
    queryset = Sensory.objects.all()
    serializer_class = SensorySerializer
    http_method_names = ['get', 'post']

    @swagger_auto_schema(responses={400: "Bad Request"})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, headers=headers)

    sensorID_parameter = openapi.Parameter('sensorID', openapi.IN_QUERY, description="ID of the sensor",
                                           type=openapi.TYPE_STRING, required=True)
    time_parameter = openapi.Parameter('time', openapi.IN_QUERY, description="search time limitation in minutes",
                                       required=False, type=openapi.TYPE_INTEGER)

    @swagger_auto_schema(manual_parameters=[sensorID_parameter, time_parameter])
    def list(self, request, *args, **kwargs):
        sensorID = request.query_params.get('sensorID')
        queryset = self.queryset.filter(sensorID__exact=sensorID)

        if request.query_params.get('date'):
            queryset = queryset.filter(
                datetime__gt=datetime.now() - timedelta(minutes=int(request.query_params.get('time'))))

        serializer = SensorySerializer(queryset, many=True)
        return Response(serializer.data)


# Customer View
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    http_method_names = ['get', 'post']

    @swagger_auto_schema(responses={400: "Bad Request", 204: "System is not running"})
    def create(self, request, *args, **kwargs):
        if len(Status.objects.all()) == 0:
            current_state = Status()
        else:
            current_state = Status.objects.all()[0]

        if not current_state.status:
            return Response("System is not running", status=204)

        response = super().create(request, *args, **kwargs)

        order_message = {'sender': models.CLOUD,
                         'title': 'Order Created',
                         'msg': json.dumps(response.data)}
        requests.post(settings['edge_repository_address'] + '/api/message/', data=order_message)
        requests.post(settings['edge_shipment_address'] + '/api/message/', data=order_message)

        order_data = Order.objects.filter(id=response.data['id'])[0]
        order_data.status += 1
        order_data.save()

        serializer = OrderSerializer(order_data)
        return Response(serializer.data, status=201)


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    http_method_names = ['post']

    # Experiment Variables
    experiment_type = 'SAS'
    dm_type = 'ORL'

    # Self-adaptive System Experiment Methods & Variables
    current_anomaly = [False] * 3
    recent_order = [None] * 3
    recent_item = [None] * 3
    reward = 0
    anomaly_aware = True
    rl_model = rl.DQN(anomaly_aware, path='../model/a_rl.pth')
    ordered = [0] * 4
    old_state = None
    old_decision = None
    old_reward = 0

    @swagger_auto_schema(responses={400: "Bad request", 204: "Invalid Message Title / Invalid Message Sender"})
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        sender = int(request.data['sender'])
        title = request.data['title']

        if sender == models.USER:
            if title == 'Start' or title == 'Stop':
                msg = json.loads(request.data['msg'])
                if len(Status.objects.all()) == 0:
                    current_state = Status()
                else:
                    current_state = Status.objects.all()[0]

                if title == 'Start':
                    self.experiment_type = msg['experiment_type']
                    self.dm_type = msg['dm_type']

                    current_state.status = True
                    current_state.experiment_type = self.experiment_type
                    current_state.dm_type = self.dm_type
                    Inventory.objects.all().delete()
                    Order.objects.all().delete()

                    if self.experiment_type == 'SAS':
                        self.current_anomaly = [False] * 3
                        self.recent_order = [None] * 3
                        self.recent_item = [None] * 3
                        self.reward = 0
                        self.rl_model = rl.DQN(self.anomaly_aware, path='../model/a_rl.pth')
                        self.ordered = [0] * 4
                        self.old_state = None
                        self.old_decision = None
                        self.old_reward = 0

                elif title == 'Stop':
                    current_state.status = False

                current_state.save()

                start_message = {'sender': models.CLOUD,
                                 'title': title,
                                 'msg': self.experiment_type}
                requests.post(settings['edge_classification_address'] + '/api/message/', data=start_message)
                requests.post(settings['edge_repository_address'] + '/api/message/', data=start_message)
                requests.post(settings['edge_shipment_address'] + '/api/message/', data=start_message)

                return Response(status=201)

            elif title == 'Reward Calculation':
                self.reward -= self.get_order(True)

                if self.dm_type == 'ORL' and self.old_state is not None:
                    self.rl_model.push_optimize(self.old_state, self.old_decision, self.reward - self.old_reward, [0, *self.get_state()])
                    self.old_state = None

                return Response(self.reward, status=201)

            return Response("Invalid Message Title", status=204)

        elif sender == models.EDGE_CLASSIFICATION:
            if title == 'Classification Processed':
                msg = json.loads(request.data['msg'])
                item_type = int(msg['item_type'])
                stored = int(msg['stored'])

                # Modify Inventory DB
                target_item = Inventory(item_type=item_type, stored=stored)
                target_item.save()
                if self.ordered[item_type - 1] != 0:
                    self.ordered[item_type - 1] -= 1

                return Response(status=201)

            elif title == 'Calculation Request':
                if self.experiment_type != 'SAS':
                    item_type = int(request.data['msg'])
                    selected_tactic = item_type - 1
                    if item_type == 4:
                        selected_tactic = 2

                    if not self.available(selected_tactic):
                        return Response(status=204)

                elif self.need_decision():
                    if self.dm_type == 'Random':
                        selected_tactic = random.choice(self.get_available())
                    else:
                        item_type = int(request.data['msg'])
                        selected_tactic = self.rl_model.select_tactic([item_type, *self.get_state()],
                                                                      self.available())
                        self.old_state = [item_type, *self.get_state()]
                        self.old_decision = selected_tactic

                elif len(self.get_available()) == 1:
                    selected_tactic = self.get_available()[0]

                else:
                    return Response(status=204)

                return Response(int(selected_tactic), status=201)

            print(title)
            return Response("Invalid Message Title", status=204)

        elif sender == models.EDGE_REPOSITORY:
            if title == 'Order Processed':
                stored = int(request.data['msg'])

                # Modify Inventory DB
                target_item = Inventory.objects.filter(stored=stored)[0]
                target_item.stored = models.SHIPMENT
                target_item.save()
                self.recent_item[stored] = target_item

                # Modify Order DB
                target_orders = Order.objects.filter(item_type=target_item.item_type, status=2)
                if len(target_orders) != 0:
                    target_orders[0].status = 3
                    target_orders[0].save()
                self.recent_order[stored] = target_orders[0]

                return Response(status=201)

            elif title == 'Anomaly Occurred':
                location = int(request.data['msg'])

                self.current_anomaly[location] = True
                self.recent_item[location].stored = models.STUCK
                self.recent_item[location].stored.save()
                self.recent_order[location].status = 2
                self.recent_order[location].save()
                self.recent_order[location] = None

                return Response(status=201)

            elif title == 'Anomaly Solved':
                location = int(request.data['msg'])

                self.current_anomaly[location] = False
                self.recent_item[location].stored = models.SHIPMENT
                self.recent_item[location].stored.save()

                orders = Order.objects.filter(status=2, item_type=self.recent_item[location].item_type)
                if len(orders) != 0:
                    orders[0].status = 3
                    orders[0].save()

                return Response(status=201)

            return Response("Invalid Message Title", status=204)

        elif sender == models.EDGE_SHIPMENT:
            if title == 'Order Processed':
                order_data = json.loads(request.data['msg'])
                item_type = int(order_data['item_type'])
                dest = order_data['dest']

                if dest == 3:
                    self.reward -= 100
                else:
                    # Modify Order DB
                    orders = Order.objects.filter(item_type=item_type, dest=dest, status=3)
                    if len(orders) != 0:
                        target_order = orders[0]
                        target_order.status = 4
                        target_order.save()
                        self.reward += 100

                return Response(status=201)

            return Response("Invalid Message Title", status=204)

        return Response("Invalid Message Sender", status=204)


    # Self-adaptive System Experiment Methods & Variables
    def available(self, i=None):
        if i is not None:
            inventory_objects = Inventory.objects.filter(stored=i)
            ans = len(inventory_objects) < settings['maximum_capacity_repository']
            if not self.anomaly_aware:
                return ans
            return ans and not self.current_anomaly[i]

        ans = []
        for i in range(3):
            inventory_objects = Inventory.objects.filter(stored=i)
            single_ans = len(inventory_objects) < settings['maximum_capacity_repository']
            if not self.anomaly_aware:
                ans.append(single_ans)
            else:
                ans.append(single_ans and not self.current_anomaly[i])
        return ans

    def need_decision(self):
        num_true = 0
        for ans in self.available():
            if ans:
                num_true += 1

        return num_true > 1

    def get_available(self):
        available = self.available()
        ans = []
        for i, avail in enumerate(available):
            if avail:
                ans.append(i)
        return ans

    def get_inventory(self, item):
        return self.ordered[item - 1] + len(Inventory.objects.filter(item_type=item))

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
                ans += item.item_type * (5 ** (settings['maximum_capacity_repository'] - i - 1))
            return ans

        ans = []
        for i in range(4):
            ans.append(repr_list(Inventory.objects.filter(stored=i)))
        ans.extend(self.get_order(False))

        if self.anomaly_aware:
            anomaly_number = 0
            for i, anomaly in enumerate(self.current_anomaly):
                if anomaly:
                    anomaly_number += (2 ** i)
            ans.append(anomaly_number)

        return ans



