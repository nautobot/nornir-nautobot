"""Used to intialize the dispatcher."""
# pylint: disable=raise-missing-from

import importlib
import logging

from nornir.core.task import Result, Task
from nornir_nautobot.exceptions import NornirNautobotException

LOGGER = logging.getLogger(__name__)

_DEFAULT_DRIVERS_MAPPING = {
    "default": "nornir_nautobot.plugins.tasks.dispatcher.default.NautobotNornirDriver",
    "default_netmiko": "nornir_nautobot.plugins.tasks.dispatcher.default.NetmikoNautobotNornirDriver",
    "cisco_asa": "nornir_nautobot.plugins.tasks.dispatcher.cisco_asa.NautobotNornirDriver",
    "cisco_nxos": "nornir_nautobot.plugins.tasks.dispatcher.cisco_nxos.NautobotNornirDriver",
    "cisco_ios": "nornir_nautobot.plugins.tasks.dispatcher.cisco_ios.NautobotNornirDriver",
    "cisco_xr": "nornir_nautobot.plugins.tasks.dispatcher.cisco_ios_xr.NautobotNornirDriver",
    "juniper_junos": "nornir_nautobot.plugins.tasks.dispatcher.juniper_junos.NautobotNornirDriver",
    "arista_eos": "nornir_nautobot.plugins.tasks.dispatcher.arista_eos.NautobotNornirDriver",
    "mikrotik_routeros_api": "nornir_nautobot.plugins.tasks.dispatcher.mikrotik_routeros_api.NautobotNornirDriver",
    "ruckus_fastiron": "nornir_nautobot.plugins.tasks.dispatcher.ruckus_fastiron.NautobotNornirDriver",
    "mikrotik_routeros": "nornir_nautobot.plugins.tasks.dispatcher.mikrotik_routeros.NautobotNornirDriver",
    "ruckus_smartzone_api": "nornir_nautobot.plugins.tasks.dispatcher.ruckus_smartzone_api.NautobotNornirDriver",
    "ruckus_access_point": "nornir_nautobot.plugins.tasks.dispatcher.ruckus_smartzone_api.NautobotNornirDriver",
}


def dispatcher(task: Task, method: str, logger, obj, *args, **kwargs) -> Result:
    """Helper Task to retrieve a given Nornir task for a given platform.

    Args:
        task (Nornir Task):  Nornir Task object.
        method (str):  The string value of the method to dynamically find.

    Returns:
        Result: Nornir Task result.
    """
    if kwargs.get("default_drivers_mapping"):
        default_drivers_mapping = kwargs["default_drivers_mapping"]
        del kwargs["default_drivers_mapping"]
    else:
        default_drivers_mapping = _DEFAULT_DRIVERS_MAPPING

    logger.log_debug(f"Executing dispatcher for {task.host.name} ({task.host.platform})")

    # Get the platform specific driver, if not available, get the default driver
    driver = default_drivers_mapping.get(task.host.platform, default_drivers_mapping.get("default"))
    logger.log_debug(f"Found driver {driver}")

    if not driver:
        logger.log_failure(
            obj, f"Unable to find the driver for {method} for platform: {task.host.platform}, preemptively failed."
        )
        raise NornirNautobotException(
            f"Unable to find the driver for {method} for platform: {task.host.platform}, preemptively failed."
        )

    module_name, class_name = driver.rsplit(".", 1)
    driver_class = getattr(importlib.import_module(module_name), class_name)

    if not driver_class:
        logger.log_failure(obj, f"Unable to locate the class {driver}, preemptively failed.")
        raise NornirNautobotException(f"Unable to locate the class {driver}, preemptively failed.")

    try:
        driver_task = getattr(driver_class, method)
    except AttributeError:
        logger.log_failure(obj, f"Unable to locate the method {method} for {driver}, preemptively failed.")
        raise NornirNautobotException(f"Unable to locate the method {method} for {driver}, preemptively failed.")

    result = task.run(task=driver_task, logger=logger, obj=obj, *args, **kwargs)

    return Result(
        host=task.host,
        result=result,
    )
