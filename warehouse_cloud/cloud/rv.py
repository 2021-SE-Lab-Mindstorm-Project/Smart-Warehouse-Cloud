import time

from runtime_verification import event, scope, property

globally_scope = scope.GloballyScope(None)

inventory_over_event = event.InventoryOverEvent("Inventory Over")
absence_property = property.Absence(inventory_over_event, globally_scope)

item_type_valid_event = event.ItemTypeValidEvent("Item Type Valid")
universality_property = property.Universality(item_type_valid_event, globally_scope)

item_number_event = event.ItemNumberEvent("Item number 1", 1)
existence_property = property.Existence(item_number_event, globally_scope)

properties = [
    absence_property,
    universality_property,
    existence_property
]


def run(seconds):
    time.sleep(seconds)
    run_verification()


def run_verification():
    for prop in properties:
        prop.check()

    for prop in properties:
        print(prop.name, prop.status)