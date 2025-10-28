"""nornir dispatcher for Mikrotik Router OS."""

# pylint: disable=raise-missing-from

import json
import ssl

try:
    import routeros_api  # pylint: disable=E0401
except ImportError:
    routeros_api = None

from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command, netmiko_send_config

from nornir_nautobot.constants import EXCEPTION_TO_ERROR_MAPPER
from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.plugins.tasks.dispatcher.default import (
    DispatcherMixin,
    NetmikoDefault,
)
from nornir_nautobot.utils.helpers import get_error_message

NETMIKO_DEVICE_TYPE = "mikrotik_routeros"


class ApiMikrotikRouteros(DispatcherMixin):
    """Default collection of Nornir Tasks based on Napalm."""

    tcp_port = 8729

    config_command = [
        "/system/identity",
        "/user",
        "/interface",
        "/ip/address",
        "/system/ntp/client",
        "/ip/dns",
        "/snmp/community",
        "/system/logging/action",
    ]

    @classmethod
    def get_config(  # pylint: disable=R0913,R0914,too-many-positional-arguments
        cls,
        task: Task,
        logger,
        obj,
        backup_file: str,
        remove_lines: list,
        substitute_lines: list,
    ) -> Result:
        """Get the latest configuration from the device.

        Args:
            task (Task): Nornir Task.
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            backup_file (str): The file location of where the back configuration should be saved.
            remove_lines (list): A list of regex lines to remove configurations.
            substitute_lines (list): A list of dictionaries with to remove and replace lines.

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        logger.debug(f"Executing get_config for {task.host.name} on {task.host.platform}")
        if not routeros_api:
            error_msg = get_error_message("E1020", dependency="routeros_api")
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)

        sslctx = ssl.create_default_context()
        sslctx.set_ciphers("ADH-AES256-GCM-SHA384:ADH-AES256-SHA256:@SECLEVEL=0")
        connection = routeros_api.RouterOsApiPool(
            task.host.hostname,
            username=task.host.username,
            password=task.host.password,
            use_ssl=True,
            ssl_context=sslctx,
            plaintext_login=True,
        )
        config_data = {}
        try:
            api = connection.get_api()
        except Exception as error:
            error_msg = get_error_message("E1021", error=error)
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)
        for endpoint in cls.config_command:
            try:
                resource = api.get_resource(endpoint)
                config_data[endpoint] = resource.get()
            except Exception as error:
                error_msg = get_error_message("E1022", error=error)
                logger.error(error_msg, extra={"object": obj})
                raise NornirNautobotException(error_msg)

        connection.disconnect()
        running_config = json.dumps(config_data, indent=4)
        processed_config = cls._process_config(logger, running_config, remove_lines, substitute_lines, backup_file)
        return Result(host=task.host, result={"config": processed_config})


class NetmikoMikrotikRouteros(NetmikoDefault):
    """Driver for Mikrotik Router OS."""

    config_command = "export terse"
    version_command = "system resource print"

    @classmethod
    def get_config(  # pylint: disable=R0913,R0914,too-many-positional-arguments
        cls,
        task: Task,
        logger,
        obj,
        backup_file: str,
        remove_lines: list,
        substitute_lines: list,
        command_file_path: str = None,
    ) -> Result:
        """Get the latest configuration from the device using Netmiko. Overrides default get_config.

        This accounts for Mikrotik Router OS config scrubbing behavior since ROS >= 7.X.

        Args:
            task (Task): Nornir Task.
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            remove_lines (list): A list of regex lines to remove configurations.
            substitute_lines (list): A list of dictionaries with to remove and replace lines.
            backup_file (str): The file location of where the back configuration should be saved.
            command_file_path (str, optional): Path to a file containing additional commands to run. Defaults to None.

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        task.host.platform = NETMIKO_DEVICE_TYPE
        logger.debug(f"Analyzing Software Version for {task.host.name} on {task.host.platform}")
        try:
            result = task.run(task=netmiko_send_command, command_string=cls.version_command)
        except NornirSubTaskError as exc:
            error_code = EXCEPTION_TO_ERROR_MAPPER.get(type(exc.result.exception), "E1016")
            error_msg = get_error_message(error_code, exc=exc)
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)

        if result[0].failed:
            return result

        major_version = result[0].result.split()[3].split(".")[0]

        command = cls._get_config_command(obj)
        if major_version > "6":
            command += " show-sensitive"

        logger.debug(f"Found Mikrotik Router OS version {major_version}")
        logger.debug(f"Executing get_config for {task.host.name} on {task.host.platform}")

        try:
            result = task.run(task=netmiko_send_command, command_string=command)
        except NornirSubTaskError as exc:
            error_msg = f"Failed with an unknown issue. `{exc.result.exception}`"
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)

        if result[0].failed:
            return result

        _running_config = result[0].result
        processed_config = cls._process_config(logger, _running_config, remove_lines, substitute_lines, backup_file)
        return Result(host=task.host, result={"config": processed_config})

    @staticmethod
    def merge_config(
        task: Task,
        logger,
        obj,
        config: str,
        can_diff: bool = True,
    ) -> Result:
        """Send configuration to merge on the device.

        Args:
            task (Task): Nornir Task.
            logger (NornirLogger): Custom NornirLogger object to reflect job_results (via Nautobot Jobs) and Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            config (str): The config set.
            can_diff (bool): Whether to use diff mode or not. Defaults to True.

        Raises:
            NornirNautobotException: Authentication error.
            NornirNautobotException: Timeout error.
            NornirNautobotException: Other exception.

        Returns:
            Result: Nornir Result object with a dict as a result containing what changed and the result of the push.
        """
        NETMIKO_FAIL_MSG = ["bad", "failed", "failure"]  # pylint: disable=C0103
        logger.info("Config merge starting", extra={"object": obj})

        try:
            config_list = config.splitlines()
            push_result = task.run(
                task=netmiko_send_config,
                config_commands=config_list,
            )
        except NornirSubTaskError as exc:
            error_msg = get_error_message("E1015", method="merge_config", exc=exc)
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg) from exc

        if any(msg in push_result[0].result.lower() for msg in NETMIKO_FAIL_MSG):
            logger.warning(
                "Config merged with errors, please check full info log below.",
                extra={"object": obj},
            )
            error_msg = get_error_message("E1028", push_result=push_result)
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)
        logger.info("Config merged successfully.", extra={"object": obj})
        logger.info(f"result: {push_result[0].result}", extra={"object": obj})
        push_result[0].failed = False
        push_result[0].changed = True

        return Result(
            host=task.host,
            result={
                "changed": push_result[0].changed,
                "result": push_result[0].result,
                "failed": push_result[0].failed,
            },
        )
