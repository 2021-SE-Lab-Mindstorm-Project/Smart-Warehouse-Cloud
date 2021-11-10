import json
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


def state():
    state = []
    for i in range(3):
        items = Inventory.objects.filter(stored=i).order_by('updated')[:int(settings['maximum_capacity_repository'])]
        ans = 0
        for j, item in enumerate(items):
            ans += item.item_type * (5 ** (int(settings['maximum_capacity_repository']) - j - 1))
        state.append(state)

    for i in range(4):
        orders = Order.objects.filter(item_type=i)
        state.append(len(orders))

    return state

def available_c():
    available = []
    for i in range(3):
        items = Inventory.objects.filter(stored=i)
        if len(items) >= settings['maximum_capacity_repository']:
            available.append(False)
        else:
            available.append(True)

    return available

def available_r(anomaly):
    available = []
    for i in range(3):
        items = Inventory.objects.filter(stored=i)
        if len(items) != 0 and not anomaly[i]:
            available.append(True)
        else:
            available.append(False)

    return available


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    http_method_names = ['post']

    ac_model = rl.DQN(10, path='../model/a_rl_c.pth')
    ar_model = rl.DQN(9, path='../model/a_rl_r.pth')
    c_model = rl.DQN(9, path='../model/rl_c.pth')
    r_model = rl.DQN(8, path='../model/rl_r.pth')

    anomaly = [False, False, False]
    recent = [None, None, None]

    @swagger_auto_schema(responses={400: "Bad request", 204: "Invalid Message Title / Invalid Message Sender"})
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        sender = int(request.data['sender'])
        title = request.data['title']

        if sender == models.USER:
            if title == 'Start' or title == 'Stop':
                if len(Status.objects.all()) == 0:
                    current_state = Status()
                else:
                    current_state = Status.objects.all()[0]

                if title == 'Start':
                    current_state.status = True
                    Inventory.objects.all().delete()
                    Order.objects.all().delete()
                elif title == 'Stop':
                    current_state.status = False

                current_state.save()

                start_message = {'sender': models.CLOUD,
                                 'title': title,
                                 'msg': ''}
                requests.post(settings['edge_classification_address'] + '/api/message/', data=start_message)
                requests.post(settings['edge_repository_address'] + '/api/message/', data=start_message)
                requests.post(settings['edge_shipment_address'] + '/api/message/', data=start_message)

                return Response(status=201)

            return Response("Invalid Message Title", status=204)

        elif sender == models.EDGE_CLASSIFICATION:
            if title == 'Classification Processed':
                msg = json.loads(request.data['msg'])
                item_type = int(msg['item_type'])
                stored = int(msg['stored'])

                # Modify Inventory DB
                target_item = Inventory(item_type=item_type, stored=stored)
                target_item.save()

                return Response(status=201)

            elif title == 'Calculation Request':
                if int(settings['anomaly_aware']) == 1:
                    selected_tactic = self.ac_model.select_tactic(state(), available_c())
                else:
                    selected_tactic = self.c_model.select_tactic(state(), available_c())
                return Response(str(int(selected_tactic)), status=201)

            return Response("Invalid Message Title", status=204)

        elif sender == models.EDGE_REPOSITORY:
            if title == 'Order Processed':
                stored = int(request.data['msg'])

                # Modify Inventory DB
                target_item = Inventory.objects.filter(stored=stored)[0]
                target_item.stored = models.SHIPMENT
                target_item.save()
                self.recent[stored] = target_item

                # Modify Order DB
                target_orders = Order.objects.filter(item_type=target_item.item_type, status=2)
                if len(target_orders) != 0:
                    target_orders[0].status = 3
                    target_orders[0].save()

                return Response(status=201)

            elif title == 'Calculation Request':
                if int(settings['anomaly_aware']) == 1:
                    selected_tactic = self.ar_model.select_tactic(state(), available_r(self.anomaly))
                else:
                    selected_tactic = self.r_model.select_tactic(state(), available_r(self.anomaly))
                return Response(str(int(selected_tactic)), status=201)

            elif title == 'Anomaly Occurred':
                location = int(request.data['msg'])

                self.anomaly[location] = True
                if self.recent[location] is not None:
                    self.recent[location].stored = 2
                    self.recent[location].save()

                return Response(status=201)

            elif title == 'Anomaly Solved':
                location = int(request.data['msg'])

                self.anomaly[location] = False
                if self.recent[location] is not None:
                    self.recent[location].stored = 3
                    self.recent[location].save()
                    self.recent[location] = None

                return Response(status=201)

            return Response("Invalid Message Title", status=204)

        elif sender == models.EDGE_SHIPMENT:
            if title == 'Order Processed':
                order_data = json.loads(request.data['msg'])
                item_type = int(order_data['item_type'])
                dest = order_data['dest']

                # Modify Order DB
                target_order = Order.objects.filter(item_type=item_type, dest=dest, status=3)[0]
                target_order.status = 4
                target_order.save()

                return Response(status=201)

            return Response("Invalid Message Title", status=204)

        return Response("Invalid Message Sender", status=204)
