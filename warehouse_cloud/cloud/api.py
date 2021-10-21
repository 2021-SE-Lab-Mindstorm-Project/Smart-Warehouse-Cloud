from datetime import datetime, timedelta

import requests
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, viewsets
from rest_framework.response import Response

from warehouse_cloud.settings import settings
from . import models
from .models import Sensory, Inventory, Order, Message


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
        sensorID = request.data['sensorID']
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

    @swagger_auto_schema(responses={400: "Bad Request"})
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)

        order_message = {'sender': models.CLOUD,
                         'title': 'Order Created',
                         'msg': response.data}
        requests.post(settings['edge_repository_address'] + '/api/message/', data=order_message)
        requests.post(settings['edge_shipment_address'] + '/api/message/', data=order_message)

        order_data = Order.objects.filter(id=response.data['id'])[0]
        order_data.status += 1
        order_data.save()

        serializer = OrderSerializer(order_data)
        return Response(serializer.data, status=201)


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    http_method_names = ['post']

    @swagger_auto_schema(responses={400: "Bad request / Invalid Message Title / Invalid Message Sender"})
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        sender = request.data['sender']

        if sender == models.EDGE_CLASSIFICATION:
            title = request.data['title']

            if title == 'Item Stored':
                item_type = request['msg']['item_type']

                # Modify Inventory DB
                target_item = Inventory.objects.filter(id=item_type)[0]
                target_item.value += 1
                target_item.updated = datetime.now()
                target_item.save()

                return Response(status=200)

            else:
                return Response({400: "Invalid Message Title"})

        elif sender == models.EDGE_REPOSITORY:
            title = request.data['title']

            if title == 'Order Processed':
                item_type = request['msg']['item_type']

                # Modify Inventory DB
                target_item = Inventory.objects.filter(id=item_type)[0]
                target_item.value -= 1
                target_item.updated = datetime.now()
                target_item.save()

                # Modify Order DB
                target_order = Order.objects.filter(item_type=item_type, status=2)[0]
                target_order.status = 3
                target_order.save()

                return Response(status=200)

            else:
                return Response({400: "Invalid Message Title"})

        elif sender == models.EDGE_SHIPMENT:
            title = request.data['title']

            if title == 'Order Processed':
                item_type = kwargs['pk']

                # Modify Order DB
                target_order = Order.objects.filter(item_type=item_type, status=3)[0]
                target_order.status = 4
                target_order.save()

                return Response(status=200)

            else:
                return Response({400: "Invalid Message Title"})

        else:
            return Response({400: "Invalid Message Sender"})
