"""default network_importer API-based driver for Mikrotik RouterOS."""

import os
import ssl
import json
import socket

try:
    import routeros_api  # pylint: disable=E0401
except ImportError:
    routeros_api = None

from netutils.config.clean import clean_config, sanitize_config
from netutils.dns import is_fqdn_resolvable
from netutils.ip import is_ip
from netutils.ping import tcp_ping

from nornir.core.task import Result, Task

from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.utils.helpers import make_folder

from .default import NautobotNornirDriver as DefaultNautobotNornirDriver


class NautobotNornirDriver(DefaultNautobotNornirDriver):
    """Default collection of Nornir Tasks based on Napalm."""

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
            logger (NornirLogger): Custom NornirLogger object to reflect job results (via Nautobot Jobs) and Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            backup_file (str): The file location of where the back configuration should be saved.
            remove_lines (list): A list of regex lines to remove configurations.
            substitute_lines (list): A list of dictionaries with to remove and replace lines.

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        logger.log_debug(f"Executing get_config for {task.host.name} on {task.host.platform}")
        sslctx = ssl.create_default_context()
        sslctx.set_ciphers("ADH-AES256-GCM-SHA384:ADH-AES256-SHA256:@SECLEVEL=0")
        try:
            connection = routeros_api.RouterOsApiPool(
                task.host.hostname,
                username=task.host.username,
                password=task.host.password,
                use_ssl=True,
                ssl_context=sslctx,
                plaintext_login=True,
            )
        except AttributeError:
            raise NornirNautobotException(  # pylint: disable=W0707
                "`routeros_api` module missing, check your environment"
            )
        config_data = {}
        try:
            api = connection.get_api()
        except Exception as error:
            logger.log_failure(obj, f"`get_config` method failed with an unexpected issue: `{error}`")
            raise NornirNautobotException(  # pylint: disable=W0707
                f"`get_config` method failed with an unexpected issue: `{error}`"
            )
        for endpoint in cls.config_command:
            try:
                resource = api.get_resource(endpoint)
                config_data[endpoint] = resource.get()
            except Exception as error:
                logger.log_failure(obj, f"`get_config` method failed with an unexpected issue: `{error}`")
                raise NornirNautobotException(  # pylint: disable=W0707
                    f"`get_config` method failed with an unexpected issue: `{error}`"
                )

        connection.disconnect()
        running_config = json.dumps(config_data, indent=4)
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

    @staticmethod
    def check_connectivity(task: Task, logger, obj) -> Result:
        """Check the connectivity to a network device.

        Args:
            task (Task): Nornir Task.
            logger (NornirLogger): Custom NornirLogger object to reflect job results (via Nautobot Jobs) and Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.

        Returns:
            Result: Nornir Result object.
        """
        if is_ip(task.host.hostname):
            ip_addr = task.host.hostname
        else:
            if not is_fqdn_resolvable(task.host.hostname):
                logger.log_failure(obj, "There was not an IP or resolvable, preemptively failed.")
                raise NornirNautobotException(
                    "There was not an IP or resolvable, preemptively failed."
                )  # pylint: disable=W0707
            ip_addr = socket.gethostbyname(task.host.hostname)

        # TODO: Allow port to be configurable, allow ssl as well
        port = 8729
        if not tcp_ping(ip_addr, port):
            logger.log_failure(obj, f"Could not connect to IP: {ip_addr} and port: {port}, preemptively failed.")
            raise NornirNautobotException(
                f"Could not connect to IP: {ip_addr} and port: {port}, preemptively failed."
            )  # pylint: disable=W0707
        if not task.host.username:
            logger.log_failure(obj, "There was no username defined, preemptively failed.")
            raise NornirNautobotException(
                "There was no username defined, preemptively failed."
            )  # pylint: disable=W0707
        if not task.host.password:
            logger.log_failure(obj, "There was no password defined, preemptively failed.")
            raise NornirNautobotException(
                "There was no password defined, preemptively failed."
            )  # pylint: disable=W0707

        return Result(host=task.host)
