"""Pytest of Nautobot Inventory."""
# Standard Library Imports
import os

# Third Party Imports
from nornir import InitNornir
from nornir import InitNornir

#
# Tests
#


def integration_host_list():
    my_nornir = InitNornir(
        inventory={
            "plugin": "NautobotInventory",
            "options": {
                "nautobot_url": os.getenv("NAUTOBOT_URL"),
                "nautobot_token": os.getenv("NAUTBOT_TOKEN"),
                "ssl_verify": False,
            },
        },
    )

    print(f"Hosts found: {len(my_nornir.inventory.hosts)}")
    print(my_nornir.inventory.hosts.keys())
    print(my_nornir.inventory.hosts["pek-leaf-03"])
    print(f"Platform test: {my_nornir.inventory.hosts['pek-leaf-03'].platform is None}")
    expected_data = {
        "id": "48884ca1-36c8-40a1-bba6-7ad9eada99c3",
        "url": "http://dockerrunner:8000/api/dcim/devices/48884ca1-36c8-40a1-bba6-7ad9eada99c3/",
        "name": "pek-leaf-03",
        "device_type": {
            "id": "b77ff7f2-c9ac-49f1-a74e-9dc32545ce1e",
            "url": "http://dockerrunner:8000/api/dcim/device-types/b77ff7f2-c9ac-49f1-a74e-9dc32545ce1e/",
            "manufacturer": {
                "id": "7aa233a3-ba26-4a4f-be03-c404f475c247",
                "url": "http://dockerrunner:8000/api/dcim/manufacturers/7aa233a3-ba26-4a4f-be03-c404f475c247/",
                "name": "Arista",
                "slug": "arista",
                "display": "Arista",
            },
            "model": "DCS-7150S-24",
            "slug": "dcs-7150s-24",
            "display": "Arista DCS-7150S-24",
        },
        "device_role": {
            "id": "bf357808-a599-45a4-aaf0-eef07e05bd8e",
            "url": "http://dockerrunner:8000/api/dcim/device-roles/bf357808-a599-45a4-aaf0-eef07e05bd8e/",
            "name": "leaf",
            "slug": "leaf",
            "display": "leaf",
        },
        "tenant": None,
        "platform": None,
        "serial": "",
        "asset_tag": None,
        "site": {
            "id": "ea6cfffa-b2e2-4ef3-b6a2-51af83233ce7",
            "url": "http://dockerrunner:8000/api/dcim/sites/ea6cfffa-b2e2-4ef3-b6a2-51af83233ce7/",
            "name": "pek",
            "slug": "pek",
            "display": "pek",
        },
        "rack": {
            "id": "1b63a6b5-2dd0-4a7d-baed-7da07cf58d1a",
            "url": "http://dockerrunner:8000/api/dcim/racks/1b63a6b5-2dd0-4a7d-baed-7da07cf58d1a/",
            "name": "pek-103",
            "display": "pek-103",
        },
        "position": 44,
        "face": {"value": "front", "label": "Front"},
        "parent_device": None,
        "status": {"value": "active", "label": "Active"},
        "primary_ip": None,
        "primary_ip4": None,
        "primary_ip6": None,
        "cluster": None,
        "virtual_chassis": None,
        "vc_position": None,
        "vc_priority": None,
        "comments": "",
        "local_context_schema": None,
        "local_context_data": None,
        "tags": [],
        "custom_fields": {},
        "config_context": {
            "cdp": True,
            "ntp": [{"ip": "10.1.1.1", "prefer": False}, {"ip": "10.2.2.2", "prefer": True}],
            "lldp": True,
            "snmp": {
                "host": [{"ip": "10.1.1.1", "version": "2c", "community": "networktocode"}],
                "contact": "John Smith",
                "location": "Network to Code - NYC | NY",
                "community": [
                    {"name": "ntc-public", "role": "RO"},
                    {"name": "ntc-private", "role": "RW"},
                    {"name": "networktocode", "role": "RO"},
                    {"name": "secure", "role": "RW"},
                ],
            },
            "aaa-new-model": False,
            "acl": {"definitions": {"named": {"PERMIT_ROUTES": ["10 permit ip any any"]}}},
            "route-maps": {
                "PERMIT_CONN_ROUTES": {"seq": 10, "type": "permit", "statements": ["match ip address PERMIT_ROUTES"]}
            },
        },
        "created": "2021-04-16",
        "last_updated": "2021-04-16T13:33:36.826973Z",
        "display": "pek-leaf-03",
    }
    print(f"Data Test: {my_nornir.inventory.hosts['pek-leaf-03'].data['pynautobot_dictionary'] == expected_data}")


if __name__ == "__main__":
    integration_host_list()
