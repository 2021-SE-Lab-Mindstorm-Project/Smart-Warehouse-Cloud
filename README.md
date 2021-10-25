# Cloud Server

## Overall Description

The cloud server has two components, messaging system, and database.

### Messaging System

Messaging system gets the messages from edge servers using Django REST framework. Messages from the edge server are
considered as a data that can be stores in the cloud server. Here are the lists of the messages that edge server sends
to the cloud.

* Item stored acknowledgement (Classification Edge)
* Order processed acknowledgement (Repository, Shipment Edge)
* Store sensory data (All)
    * `/sensory/` with `post` method

Also, customers can order items, and developers can get the sensory data from the cloud by using APIs.

* `/order/` with `get`, `post` method
* `/sensory/` with `get` method

When the order is made, the cloud automatically send the request to the repository, and shipment edge.

### Database

Database is based on the SQLite 3, with django. Here are the databases of the cloud server.

### Inventory

|Fields|Type|Choices|
|-------|-----|-----|
|item_type|Char|Red, White, Yellow|
|value|Int||
|updated|Datetime||

### Order

|Fields|Type|Choices|
|-------|-----|-----|
|order_made|Datetime||
|order_completed|Datetime||
|item_type|Char|Red, White, Yellow|
|order_status|Int|Order Status|

#### Order Status

1. Order Received
2. Repository Processing
3. Shipment Processing
4. Order Completed

### Sensory

|Fields|Type|Choices|
|-------|-----|-----|
|sensorID|Char||
|value|Float||
|datetime|Datetime||

## Run the cloud server

### Prerequisite

* Python 3.9

### Running Manual

1. Clone this repository `git clone https://github.com/2021-SE-Lab-Mindstorm-Project/Smart-Warehouse-Cloud`
2. Move to `Smart-Warehouse-Cloud`
3. Make `secrets.json` with `{"django_secret_key": "YOUR_KEY"}`
4. Configure `settings.json` with appropriate values.
5. Make python venv and install requirements with `requirements.txt`
6. Move to `warehouse_cloud` folder.
7. `python manage.py migrate`
8. `python manage.py runserver 0.0.0.0:80`
