import json
import random
from datetime import datetime, timedelta

import requests
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, viewsets
from rest_framework.response import Response
from warehouse_cloud.settings import settings

from . import models, warehouse
from .models import Sensory, Inventory, Order, Message, Status

# Experiment Variables
experiment_type = 'SAS'
dm_type = 'ORL'
target = warehouse.Warehouse(True)

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
        order_data = Order.objects.filter(id=response.data['id'])[0]

        order_message = {'sender': models.CLOUD,
                         'title': 'Order Created',
                         'msg': json.dumps(response.data)}

        item_type = response.data['item_type']
        shipment_ready = Inventory.objects.filter(item_type=item_type, stored=3)
        order_shipment = Order.objects.filter(item_type=item_type, status=3)

        if experiment_type == 'SAS':
            for i in range(3):
                if target.stuck[i]:
                    shipment_ready += 1

        if len(shipment_ready) <= len(order_shipment):
            requests.post(settings['edge_repository_address'] + '/api/message/', data=order_message)
            order_data.status = 2
            order_data.save()
        else:
            order_data.status = 3
            order_data.save()

        requests.post(settings['edge_shipment_address'] + '/api/message/', data=order_message)
        serializer = OrderSerializer(order_data)
        return Response(serializer.data, status=201)


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    http_method_names = ['post']

    @swagger_auto_schema(responses={400: "Bad request", 204: "Invalid Message Title / Invalid Message Sender"})
    def create(self, request, *args, **kwargs):
        global experiment_type, dm_type, target
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
                    experiment_type = msg['experiment_type']

                    current_state.status = True
                    Inventory.objects.all().delete()
                    Order.objects.all().delete()

                    if experiment_type == 'SAS':
                        dm_type = msg['dm_type']
                        if dm_type == 'AAAA':
                            target = warehouse.Warehouse(True)
                        else:
                            target = warehouse.Warehouse(False)

                elif title == 'Stop':
                    current_state.status = False

                current_state.save()

                start_message = {'sender': models.CLOUD,
                                 'title': title,
                                 'msg': experiment_type}
                requests.post(settings['edge_classification_address'] + '/api/message/', data=start_message)
                requests.post(settings['edge_repository_address'] + '/api/message/', data=start_message)
                requests.post(settings['edge_shipment_address'] + '/api/message/', data=start_message)

                return Response(status=201)

            elif title == 'Process':
                msg = json.loads(request.data['msg'])
                anomaly_0 = False if int(msg['anomaly_0']) == 0 else True
                anomaly_2 = False if int(msg['anomaly_2']) == 0 else True

                num_orders = len(Order.objects.all()) - len(Order.objects.filter(status=4))
                if num_orders == 0 and target.tick > target.order_total:
                    result = {
                        'tick': target.tick,
                        'reward': target.reward,
                        'alert': "ended"
                    }
                    current_state = Status.objects.all()[0]
                    current_state.status = False
                    current_state.save()

                    start_message = {'sender': models.CLOUD,
                                     'title': "Stop",
                                     'msg': experiment_type}
                    requests.post(settings['edge_classification_address'] + '/api/message/', data=start_message)
                    requests.post(settings['edge_repository_address'] + '/api/message/', data=start_message)
                    requests.post(settings['edge_shipment_address'] + '/api/message/', data=start_message)

                    return Response(result, status=201)

                target.reward -= num_orders * target.reward_wait
                target.tick += 1

                # ORL
                if dm_type == 'ORL' and target.old_state is not None:
                    target.rl_model.push_optimize(target.old_state, target.old_decision,
                                                  target.reward - target.old_reward, target.get_state())
                    target.old_state = None
                    target.old_reward = target.reward

                # New anomaly
                if target.current_anomaly[0] == -1 and anomaly_0:
                    target.current_anomaly[0] = target.tick
                if target.current_anomaly[2] == -1 and anomaly_2:
                    target.current_anomaly[2] = target.tick

                # Move c to r
                c_decision = 3
                # Decision making
                if target.need_decision():
                    if dm_type == 'Random':
                        candidate = target.get_available()
                        if len(candidate) != 0:
                            c_decision = random.choice(candidate)
                    else:
                        target.old_state = target.get_state()
                        model = target.rl_model
                        if target.anomaly_state() != 0 and dm_type == 'AAAA':
                            if target.current_anomaly[0] != -1:
                                model = target.a_rl_models[0]
                            else:
                                model = target.a_rl_models[2]
                        target.old_decision = model.select_tactic(target.get_state(), target.available())
                        c_decision = int(target.old_decision)

                elif target.recent_c != 0:
                    avail = target.get_available()
                    if len(avail) != 0:
                        c_decision = avail[0]

                # R to S
                r_decision = [False] * 3
                s_items = Inventory.objects.filter(stored=3)
                shipment_cap = target.cap_conveyor - len(s_items) - target.stuck.count(True)
                for i in [1, 0, 2]:
                    inventory_list = Inventory.objects.filter(stored=i)
                    if not target.stuck[i] and len(inventory_list) != 0 and shipment_cap > 0:
                        target_item = inventory_list[0]
                        orders = Order.objects.filter(item_type=target_item.item_type, status=2).order_by('made')
                        if len(orders) != 0:
                            r_decision[i] = True
                            shipment_cap -= 1
                            target.r_wait[i] = 0
                            orders[0].status = 3
                            orders[0].save()
                        elif target.r_wait[i] > target.cap_wait:
                            r_decision[i] = True
                            shipment_cap -= 1
                            target.r_wait[i] = 0
                        else:
                            target.r_wait[i] += 1

                # Make stuck
                for i in [0, 2]:
                    if target.current_anomaly[i] != -1 and r_decision[i] and target.stuck[i] == 0:
                        target.stuck[i] = True
                        r_decision[i] = False
                        target.count[i] += 1

                    elif target.current_anomaly[i] != -1 and target.stuck[i] and target.count[i] < target.anomaly_wait:
                        target.count[i] += 1

                    elif target.current_anomaly[i] != -1 and target.stuck[i] and target.count[i] == target.anomaly_wait:
                        target.count[i] = 0
                        r_decision[i] = True
                        target.stuck[i] = False

                # Solve anomaly
                for i in [0, 2]:
                    if target.current_anomaly[i] != -1 and target.current_anomaly[i] + target.anomaly_duration < target.tick:
                        if target.stuck[i]:
                            r_decision[i] = True
                            target.stuck[i] = False
                        target.count[i] = 0
                        target.current_anomaly[i] = -1

                # s
                s_decision = 3
                if target.recent_s != 0:
                    target_item = Inventory.objects.filter(item_type=target.recent_s, stored=3)[0]
                    orders = Order.objects.filter(item_type=target_item.item_type, status=3).order_by('made')
                    if len(orders) != 0:
                        s_decision = orders[0].dest
                        target.s_wait = 0
                    elif target.s_wait > target.cap_wait:
                        s_decision = -1
                        target.s_wait = 0
                    else:
                        target.s_wait += 1

                # Request Item
                request = ''
                for i in range(1, 5):
                    need = len(Order.objects.filter(item_type=i)) - len(Order.objects.filter(item_type=i, status=4))
                    if target.get_inventory(i) < need:
                        target.c[i - 1] += target.item_buy
                        request += str(i) + ' &'

                inventories = []
                for i in range(4):
                    items = Inventory.objects.filter(stored=i).order_by('updated')
                    ans = ''
                    for item in items:
                        ans += str(item.item_type) + ','
                    inventories.append(ans)

                result = {
                    'tick': target.tick - 1,
                    'reward': target.reward,
                    'request': request,
                    'recent_c': target.recent_c,
                    'c_decision': c_decision,
                    'r_decision': r_decision,
                    's_decision': s_decision,
                    'anomaly_0': 1 if target.current_anomaly[0] != -1 else 0,
                    'anomaly_2': 1 if target.current_anomaly[2] != -1 else 0,
                    'stuck_0': 1 if target.stuck[0] else 0,
                    'stuck_2': 1 if target.stuck[2] else 0,
                    'inventory_0': inventories[0],
                    'inventory_1': inventories[1],
                    'inventory_2': inventories[2],
                    'inventory_3': inventories[3],
                    'order_r_1': len(Order.objects.filter(item_type=1, status=2)),
                    'order_r_2': len(Order.objects.filter(item_type=2, status=2)),
                    'order_r_3': len(Order.objects.filter(item_type=3, status=2)),
                    'order_r_4': len(Order.objects.filter(item_type=4, status=2)),
                    'order_s_1': len(Order.objects.filter(item_type=1, status=3)),
                    'order_s_2': len(Order.objects.filter(item_type=2, status=3)),
                    'order_s_3': len(Order.objects.filter(item_type=3, status=3)),
                    'order_s_4': len(Order.objects.filter(item_type=4, status=3))
                }

                target.c_allow = c_decision
                target.r_allow = r_decision
                target.s_allow = s_decision

                return Response(result, status=201)

            return Response("Invalid Message Title", status=204)

        elif sender == models.EDGE_CLASSIFICATION:
            if title == 'Classification Processed':
                msg = json.loads(request.data['msg'])
                item_type = int(msg['item_type'])
                stored = int(msg['stored'])

                target.c_allow = 3
                target.recent_c = 0

                # Modify Inventory DB
                target_item = Inventory(item_type=item_type, stored=stored)
                target_item.save()
                if target.c[item_type - 1] != 0:
                    target.c[item_type - 1] -= 1

                return Response(status=201)

            elif title == 'SAS Check':
                target.recent_c = int(request.data['msg'])

                if target.c_allow == 3:
                    return Response(status=204)

                selected_tactic = target.c_allow
                return Response(int(selected_tactic), status=201)

            return Response("Invalid Message Title", status=204)

        elif sender == models.EDGE_REPOSITORY:
            if title == 'Order Processed':
                stored = int(request.data['msg'])
                target.r_allow[stored] = False

                # Modify Inventory DB
                target_item = Inventory.objects.filter(stored=stored)[0]
                target_item.stored = models.SHIPMENT
                target_item.save()

                # Modify Order DB
                if experiment_type != 'SAS':
                    target_orders = Order.objects.filter(item_type=target_item.item_type, status=2)
                    if len(target_orders) != 0:
                        target_orders[0].status = 3
                        target_orders[0].save()

                return Response(status=201)

            elif title == 'SAS Check':
                location = int(request.data['msg'])
                if not target.r_allow[location]:
                    return Response(status=204)

                return Response(status=201)

            elif title == 'Anomaly Occurred':
                location = int(request.data['msg'])
                return Response(status=201)

            elif title == 'Anomaly Solved':
                location = int(request.data['msg'])
                return Response(status=201)

            return Response("Invalid Message Title", status=204)

        elif sender == models.EDGE_SHIPMENT:
            if title == 'Order Processed':
                order_data = json.loads(request.data['msg'])
                item_type = int(order_data['item_type'])
                dest = order_data['dest']

                target.s_allow = 3
                target.recent_s = 0

                # Modify Inventory DB
                target_item = Inventory.objects.filter(item_type=item_type,
                                                       stored=models.SHIPMENT).order_by('updated')[0]
                target_item.stored = models.COMPLETED
                target_item.save()

                if dest == -1:
                    target.reward -= target.reward_trash
                else:
                    # Modify Order DB
                    orders = Order.objects.filter(item_type=item_type, dest=dest, status=3)
                    if len(orders) != 0:
                        target_order = orders[0]
                        target_order.status = 4
                        target_order.save()
                        target.reward += target.reward_order

                return Response(status=201)

            elif title == 'SAS Check':
                target.recent_s = int(request.data['msg'])

                items = Inventory.objects.filter(item_type=target.recent_s,
                                                 stored=models.SHIPMENT).order_by('updated')
                if len(items) == 0:
                    idx = 0
                    while idx < 5:
                        rep = Inventory.objects.filter(stored=1).order_by('updated')
                        if len(rep) > idx and rep[idx].item_type == target.recent_s:
                            rep[0].stored = 3
                            rep[0].save()
                            break

                        rep = Inventory.objects.filter(stored=0).order_by('updated')
                        if len(rep) > idx and rep[idx].item_type == target.recent_s:
                            rep[0].stored = 3
                            rep[0].save()
                            break

                        rep = Inventory.objects.filter(stored=2).order_by('updated')
                        if len(rep) > idx and rep[idx].item_type == target.recent_s:
                            rep[0].stored = 3
                            rep[0].save()
                            break

                        idx += 1

                if target.s_allow == 3:
                    return Response(status=204)

                selected_tactic = target.s_allow
                return Response(int(selected_tactic), status=201)

            return Response("Invalid Message Title", status=204)

        return Response("Invalid Message Sender", status=204)

