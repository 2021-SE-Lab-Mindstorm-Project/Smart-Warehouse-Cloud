import json
from datetime import datetime, timedelta

import requests
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, viewsets
from rest_framework.response import Response

from warehouse_cloud.settings import settings
from . import models
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


def initialize_inventory():
    Inventory.objects.all().delete()
    red_inventory = Inventory(item_type=1, value=0)
    white_inventory = Inventory(item_type=2, value=0)
    yellow_inventory = Inventory(item_type=3, value=0)

    red_inventory.save()
    white_inventory.save()
    yellow_inventory.save()


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    http_method_names = ['post']

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
                    initialize_inventory()
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
                item_type = int(request.data['msg'])

                # Modify Inventory DB
                target_item = Inventory.objects.filter(item_type=item_type)[0]
                target_item.value += 1
                target_item.updated = datetime.now()
                target_item.save()

                return Response(status=201)

            return Response("Invalid Message Title", status=204)

        elif sender == models.EDGE_REPOSITORY:
            if title == 'Order Processed':
                item_type = int(request.data['msg'])

                # Modify Inventory DB
                target_item = Inventory.objects.filter(item_type=item_type)[0]
                target_item.value -= 1
                target_item.updated = datetime.now()
                target_item.save()

                # Modify Order DB
                target_order = Order.objects.filter(item_type=item_type, status=2)[0]
                target_order.status = 3
                target_order.save()

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
