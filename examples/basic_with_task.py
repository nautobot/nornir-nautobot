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
            "nautobot_url": "http://localhost:8080/",
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
    result = my_nornir.run(
        task=dispatcher,
        logger=LOGGER,
        method="get_config",
        obj=nr_obj,
        framework="netmiko",
        backup_file="./ios.cfg",
        remove_lines=None,
        substitute_lines=None,
    )
    print_result(result)
