"""Example with a actual dispatcher task."""

import logging
import os
from nornir import InitNornir
from nornir_utils.plugins.functions import print_result
from nornir_nautobot.plugins.tasks.dispatcher import dispatcher


LOGGER = logging.getLogger(__name__)

my_nornir = InitNornir(
    inventory={
        "plugin": "NautobotInventory",
        "options": {
            "nautobot_url": "http://localhost:8080",
            "nautobot_token": "0123456789abcdef0123456789abcdef01234567",
            "filter_parameters": {"location": "Site 1"},
            "ssl_verify": False,
        },
    },
)
my_nornir.inventory.defaults.username = os.getenv("NORNIR_USERNAME")
my_nornir.inventory.defaults.password = os.getenv("NORNIR_PASSWORD")

for nr_host, nr_obj in my_nornir.inventory.hosts.items():
    network_driver = my_nornir.inventory.hosts[nr_host].platform
    my_nornir.inventory.hosts[nr_host].platform = "ios"
    result = my_nornir.run(
        task=dispatcher,
        logger=LOGGER,
        method="get_command",
        obj=nr_host,
        framework="napalm",
        command="get_facts",
    )
    print_result(result)

for nr_host, nr_obj in my_nornir.inventory.hosts.items():
    network_driver = my_nornir.inventory.hosts[nr_host].platform
    my_nornir.inventory.hosts[nr_host].platform = "ios"
    result = my_nornir.run(
        task=dispatcher,
        logger=LOGGER,
        method="get_command",
        obj=nr_host,
        framework="netmiko",
        command="show version",
    )
    print_result(result)