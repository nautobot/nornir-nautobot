"""Used to initialize the dispatcher."""

# pylint: disable=raise-missing-from

import logging

from nornir.core.task import Result, Task
from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.utils.helpers import snake_to_title_case, import_string

LOGGER = logging.getLogger(__name__)
PATH_ROOT = "nornir_nautobot.plugins.tasks.dispatcher.default"


def dispatcher(  # pylint: disable=too-many-arguments,too-many-locals
    task: Task, method: str, logger, obj, framework, *args, **kwargs
) -> Result:
    """Helper Task to retrieve a given Nornir task for a given platform.

    Args:
        task: Nornir Task object.
        method: The string value of the method to dynamically find.

    Returns:
        Result: Nornir Task result object.
    """
    custom_dispatcher = ""
    if kwargs.get("custom_dispatcher"):
        custom_dispatcher = kwargs["custom_dispatcher"]
        del kwargs["custom_dispatcher"]

    logger.debug(f"Dispatcher process started for {task.host.name} ({task.host.platform})")

    network_driver = task.host.platform
    network_driver_title = snake_to_title_case(network_driver)
    framework_path = (
        f"nornir_nautobot.plugins.tasks.dispatcher.{network_driver}.{framework.title()}{network_driver_title}"
    )
    framework_default_path = f"nornir_nautobot.plugins.tasks.dispatcher.default.{framework.title()}Default"

    if custom_dispatcher:
        driver_class = import_string(custom_dispatcher)
        checked_path = [custom_dispatcher]
    elif import_string(framework_path):
        driver_class = import_string(framework_path)
        checked_path = [framework_path]
    else:
        driver_class = import_string(framework_default_path)
        checked_path = [framework_path, framework_default_path]

    if not driver_class:
        error_msg = f"`E1001:` Did not find a valid dispatcher in {checked_path}, preemptively failed."
        logger.error(error_msg, extra={"object": obj})
        raise NornirNautobotException(error_msg)

    try:
        driver_task = getattr(driver_class, method)
    except AttributeError:
        error_msg = f"`E1002:` Unable to locate the method {method} for {driver_class}, preemptively failed."
        logger.error(error_msg, extra={"object": obj})
        raise NornirNautobotException(error_msg)

    result = task.run(task=driver_task, logger=logger, obj=obj, *args, **kwargs)

    return Result(
        host=task.host,
        result=result,
    )
