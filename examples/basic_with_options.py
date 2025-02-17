"""Example with a actual dispatcher task."""

import logging
import os
from netutils.lib_mapper import NAPALM_LIB_MAPPER_REVERSE
from nornir import InitNornir
from nornir.core.inventory import ConnectionOptions
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
    my_nornir.inventory.hosts[nr_host].connection_options = {
        "scrapli": ConnectionOptions(extras={"auth_strict_key": False})
    }
    network_driver = my_nornir.inventory.hosts[nr_host].data["pynautobot_object"].platform.network_driver
    my_nornir.inventory.hosts[nr_host].platform = NAPALM_LIB_MAPPER_REVERSE.get(network_driver)
    result = my_nornir.run(
        task=dispatcher,
        logger=LOGGER,
        method="get_config",
        obj=nr_host,
        framework="scrapli",
        backup_file="./ios.cfg",
        remove_lines=[{"regex": r"^Building\s+configuration.*\n"}],
        substitute_lines=[
            {
                "regex": r"^(enable (password|secret)( level \d+)? \d) .+$",
                "replace": r"\1 <removed>",
            }
        ],
    )
    print_result(result)
