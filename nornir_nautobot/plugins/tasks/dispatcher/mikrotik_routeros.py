"""network_importer driver for Mikrotik Router OS."""

import os

try:
    from netmiko.ssh_exception import NetmikoAuthenticationException, NetmikoTimeoutException
except ImportError:
    from netmiko import NetmikoAuthenticationException, NetmikoTimeoutException

from netutils.config.clean import clean_config, sanitize_config
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command

from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.utils.helpers import make_folder
from .default import NetmikoNautobotNornirDriver as DefaultNautobotNornirDriver

GET_VERSION_COMMAND = "system resource print"
GET_CONFIG_COMMAND = "export terse"
NETMIKO_DEVICE_TYPE = "mikrotik_routeros"


class NautobotNornirDriver(DefaultNautobotNornirDriver):
    """Driver for Mikrotik Router OS."""

    @staticmethod
    def get_config(task: Task, logger, obj, backup_file: str, remove_lines: list, substitute_lines: list) -> Result:
        """Get the latest configuration from the device using Netmiko. Overrides default get_config.
        
        This accounts for Mikrotik Router OS config scrubbing behavior since ROS >= 7.X.

        Args:
            task (Task): Nornir Task.
            logger (NornirLogger): Custom NornirLogger object to reflect job results (via Nautobot Jobs) and Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            remove_lines (list): A list of regex lines to remove configurations.
            substitute_lines (list): A list of dictionaries with to remove and replace lines.

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        task.host.platform = NETMIKO_DEVICE_TYPE
        logger.log_debug(f"Analyzing Software Version for {task.host.name} on {task.host.platform}")
        command = GET_VERSION_COMMAND
        try:
            result = task.run(task=netmiko_send_command, command_string=GET_VERSION_COMMAND)
        except NornirSubTaskError as exc:
            if isinstance(exc.result.exception, NetmikoAuthenticationException):
                logger.log_failure(obj, f"Failed with an authentication issue: `{exc.result.exception}`")
                raise NornirNautobotException(f"Failed with an authentication issue: `{exc.result.exception}`")

            if isinstance(exc.result.exception, NetmikoTimeoutException):
                logger.log_failure(obj, f"Failed with a timeout issue. `{exc.result.exception}`")
                raise NornirNautobotException(f"Failed with a timeout issue. `{exc.result.exception}`")

            logger.log_failure(obj, f"Failed with an unknown issue. `{exc.result.exception}`")
            raise NornirNautobotException(f"Failed with an unknown issue. `{exc.result.exception}`")

        if result[0].failed:
            return result

        major_version = result[0].result.split()[3].split('.')[0]

        command = GET_CONFIG_COMMAND
        if major_version > "6":
            command += " show-sensitive"

        logger.log_debug(f"Found Mikrotik Router OS version {major_version}")
        logger.log_debug(f"Executing get_config for {task.host.name} on {task.host.platform}")

        try:
            result = task.run(task=netmiko_send_command, command_string=command)
        except NornirSubTaskError as exc:
            logger.log_failure(obj, f"Failed with an unknown issue. `{exc.result.exception}`")
            raise NornirNautobotException(f"Failed with an unknown issue. `{exc.result.exception}`")

        if result[0].failed:
            return result

        running_config = result[0].result

        if remove_lines:
            logger.log_debug("Removing lines from configuration based on `remove_lines` definition")
            running_config = clean_config(running_config, remove_lines)
        if substitute_lines:
            logger.log_debug("Substitute lines from configuration based on `substitute_lines` definition")
            running_config = sanitize_config(running_config, substitute_lines)

        make_folder(os.path.dirname(backup_file))

        with open(backup_file, "w", encoding="utf8") as filehandler:
            filehandler.write(running_config)
        return Result(host=task.host, result={"config": running_config})
