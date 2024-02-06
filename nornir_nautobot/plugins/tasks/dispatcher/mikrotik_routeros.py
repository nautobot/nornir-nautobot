"""nornir dispatcher for Mikrotik Router OS."""

# pylint: disable=raise-missing-from

import os
import ssl
import json

try:
    import routeros_api  # pylint: disable=E0401
except ImportError:
    routeros_api = None

from netutils.config.clean import clean_config, sanitize_config

from netmiko import NetmikoAuthenticationException, NetmikoTimeoutException

from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command, netmiko_send_config

from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.plugins.tasks.dispatcher.default import DispatcherMixin, NetmikoDefault
from nornir_nautobot.utils.helpers import make_folder

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
    def get_config(  # pylint: disable=R0913,R0914
        cls, task: Task, logger, obj, backup_file: str, remove_lines: list, substitute_lines: list
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
            error_msg = "`E1020:` The `routeros_api` is not installed in this environment."
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
            error_msg = f"`E1021:` The `get_config` method failed with an unexpected issue: `{error}`"
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)
        for endpoint in cls.config_command:
            try:
                resource = api.get_resource(endpoint)
                config_data[endpoint] = resource.get()
            except Exception as error:
                error_msg = f"`E1022:` The `get_config` method failed with an unexpected issue: `{error}`"
                logger.error(error_msg, extra={"object": obj})
                raise NornirNautobotException(error_msg)

        connection.disconnect()
        running_config = json.dumps(config_data, indent=4)
        if remove_lines:
            logger.debug("Removing lines from configuration based on `remove_lines` definition")
            running_config = clean_config(running_config, remove_lines)

        if substitute_lines:
            logger.debug("Substitute lines from configuration based on `substitute_lines` definition")
            running_config = sanitize_config(running_config, substitute_lines)

        make_folder(os.path.dirname(backup_file))

        with open(backup_file, "w", encoding="utf8") as filehandler:
            filehandler.write(running_config)
        return Result(host=task.host, result={"config": running_config})


class NetmikoMikrotikRouteros(NetmikoDefault):
    """Driver for Mikrotik Router OS."""

    config_command = "export terse"
    version_command = "system resource print"

    @classmethod
    def get_config(  # pylint: disable=R0913,R0914
        cls, task: Task, logger, obj, backup_file: str, remove_lines: list, substitute_lines: list
    ) -> Result:
        """Get the latest configuration from the device using Netmiko. Overrides default get_config.

        This accounts for Mikrotik Router OS config scrubbing behavior since ROS >= 7.X.

        Args:
            task (Task): Nornir Task.
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            remove_lines (list): A list of regex lines to remove configurations.
            substitute_lines (list): A list of dictionaries with to remove and replace lines.

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        task.host.platform = NETMIKO_DEVICE_TYPE
        logger.debug(f"Analyzing Software Version for {task.host.name} on {task.host.platform}")
        try:
            result = task.run(task=netmiko_send_command, command_string=cls.version_command)
        except NornirSubTaskError as exc:
            if isinstance(exc.result.exception, NetmikoAuthenticationException):
                error_msg = f"`E1017:` Failed with an authentication issue: `{exc.result.exception}`"
                logger.error(error_msg, extra={"object": obj})
                raise NornirNautobotException(error_msg)

            if isinstance(exc.result.exception, NetmikoTimeoutException):
                error_msg = f"`E1018:` Failed with a timeout issue. `{exc.result.exception}`"
                logger.error(error_msg, extra={"object": obj})
                raise NornirNautobotException(error_msg)

            error_msg = f"`E1016:` Failed with an unknown issue. `{exc.result.exception}`"
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)

        if result[0].failed:
            return result

        major_version = result[0].result.split()[3].split(".")[0]

        command = cls.config_command
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

        _running_config = cls._remove_lines(logger, _running_config, remove_lines)
        _running_config = cls._substitute_lines(logger, _running_config, substitute_lines)
        cls._save_file(logger, backup_file, _running_config)

        return Result(host=task.host, result={"config": _running_config})

    @staticmethod
    def merge_config(
        task: Task,
        logger,
        obj,
        config: str,
    ) -> Result:
        """Send configuration to merge on the device.

        Args:
            task (Task): Nornir Task.
            logger (NornirLogger): Custom NornirLogger object to reflect job_results (via Nautobot Jobs) and Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            config (str): The config set.

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
            error_msg = f"`E1015 `Failed with error: `{exc.result.exception}`"
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg) from exc

        if any(msg in push_result[0].result.lower() for msg in NETMIKO_FAIL_MSG):
            logger.warning("Config merged with errors, please check full info log below.", extra={"object": obj})
            error_msg = f"`E1026:` result: {push_result[0].result}"
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
