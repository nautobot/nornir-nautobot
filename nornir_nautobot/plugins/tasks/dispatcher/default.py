"""default driver for the network_importer."""
# pylint: disable=raise-missing-from,too-many-arguments

import os
import socket
import jinja2

from netmiko.ssh_exception import NetmikoAuthenticationException, NetmikoTimeoutException
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import Result, Task
from nornir_jinja2.plugins.tasks import template_file
from nornir_napalm.plugins.tasks import napalm_get
from nornir_netmiko.tasks import netmiko_send_command
from netutils.config.compliance import compliance
from netutils.config.clean import clean_config, sanitize_config
from netutils.ip import is_ip
from netutils.dns import is_fqdn_valid
from netutils.ping import tcp_ping

from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.utils.helpers import make_folder


RUN_COMMAND_MAPPING = {
    "default": "show run",
    "cisco_nxos": "show run",
    "cisco_ios": "show run",
    "cisco_xr": "show run",
    "juniper_junos": "show configuration | display set",
    "arista_eos": "show run",
}


class NautobotNornirDriver:
    """Default collection of Nornir Tasks based on Napalm."""

    @staticmethod
    def get_config(task: Task, logger, obj, backup_file: str, remove_lines: list, substitute_lines: list) -> Result:
        """Get the latest configuration from the device.

        Args:
            task (Task): Nornir Task.
            logger (NornirLogger): Custom NornirLogger object to reflect job_results (via Nautobot Jobs) and Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            backup_file (str): The file location of where the back configuration should be saved.
            remove_lines (list): A list of regex lines to remove configurations.
            substitute_lines (list): A list of dictionaries with to remove and replace lines.

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        logger.log_debug(f"Executing get_config for {task.host.name} on {task.host.platform}")

        # TODO: Find standard napalm exceptions and account for them
        try:
            result = task.run(task=napalm_get, getters=["config"], retrieve="running")
        except NornirSubTaskError as exc:
            logger.log_failure(obj, f"Failed with a unknown issue. `{exc.result.exception}`")
            raise NornirNautobotException()

        if result[0].failed:
            logger.log_failure(obj, f"Failed with a unknown issue. `{str(result.exception)}`")
            return result

        running_config = result[0].result.get("config", {}).get("running", None)
        if remove_lines:
            logger.log_debug("Removing lines from configuration based on `remove_lines` definition")
            running_config = clean_config(running_config, remove_lines)

        if substitute_lines:
            logger.log_debug("Substitute lines from configuration based on `substitute_lines` definition")
            running_config = sanitize_config(running_config, substitute_lines)

        make_folder(os.path.dirname(backup_file))

        with open(backup_file, "w") as filehandler:
            filehandler.write(running_config)
        return Result(host=task.host, result={"config": running_config})

    @staticmethod
    def check_connectivity(task: Task, logger, obj) -> Result:
        """Check the connectivity to a network device.

        Args:
            task (Task): Nornir Task.
            logger (NornirLogger): Custom NornirLogger object to reflect job_results (via Nautobot Jobs) and Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.

        Returns:
            Result: Nornir Result object.
        """
        if is_ip(task.host.hostname):
            ip_addr = task.host.hostname
        else:
            if not is_fqdn_valid(task.host.hostname):
                logger.log_failure(obj, "not an IP or resolvable.")
                raise NornirNautobotException("not an IP or resolvable.")
            ip_addr = socket.gethostbyname(task.host.hostname)

        # TODO: Allow port to be configurable
        port = 22
        if not tcp_ping(ip_addr, port):
            logger.log_failure(obj, f"Attempting to connect to IP: {ip_addr} and port: {port} failed.")
            raise NornirNautobotException(f"Attempting to connect to IP: {ip_addr} and port: {port} failed.")
        if not task.host.username:
            logger.log_failure(obj, "There was no username defined, preemptively failed.")
            raise NornirNautobotException("There was no username defined, preemptively failed.")
        if not task.host.password:
            logger.log_failure(obj, "There was no password defined, preemptively failed.")
            raise NornirNautobotException("There was no password defined, preemptively failed.")

        return Result(host=task.host)

    @staticmethod
    def compliance_config(
        task: Task, logger, obj, features: str, backup_file: str, intended_file: str, platform: str
    ) -> Result:
        """Compare two configurations against each other.

        Args:
            task (Task): Nornir Task.
            logger (NornirLogger): Custom NornirLogger object to reflect job_results (via Nautobot Jobs) and Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            features (dict): A dictionary describing the configurations required.
            backup_file (str): The file location of where the back configuration should be saved.
            intended_file (str):  The file location of where the intended configuration should be saved.
            platform (str): The platform slug of the device.

        Returns:
            Result: Nornir Result object with a feature_data key of the compliance data.
        """
        if not os.path.exists(backup_file):
            logger.log_failure(obj, f"Backup file Not Found at location: `{backup_file}`")
            raise NornirNautobotException()

        if not os.path.exists(intended_file):
            logger.log_failure(obj, f"Intended config file NOT Found at location: `{intended_file}`")
            raise NornirNautobotException()

        try:
            feature_data = compliance(features, backup_file, intended_file, platform)
        except Exception as error:  # pylint: disable=broad-except
            logger.log_failure(obj, f"UNKNOWN Failure of: {str(error)}")
            raise NornirNautobotException()
        return Result(host=task.host, result={"feature_data": feature_data})

    @staticmethod
    def generate_config(
        task: Task, logger, obj, jinja_template: str, jinja_root_path: str, output_file_location: str
    ) -> Result:
        """A small wrapper around template_file Nornir task.

        Args:
            task (Task): Nornir Task.
            logger (NornirLogger): Custom NornirLogger object to reflect job_results (via Nautobot Jobs) and Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            jinja_template (str): The file location of the actual Jinja template.
            jinja_root_path (str): The file folder where the file will be saved to.
            output_file_location (str): The filename where the file will be saved to.

        Returns:
            Result: Nornir Result object.
        """
        try:
            filled_template = task.run(
                **task.host.data,
                task=template_file,
                template=jinja_template,
                path=jinja_root_path,
            )[0].result
        except NornirSubTaskError as exc:
            if isinstance(exc.result.exception, jinja2.exceptions.UndefinedError):  # pylint: disable=no-else-raise
                logger.log_failure(
                    obj,
                    f"There was a jinja2.exceptions.UndefinedError error: ``{str(exc.result.exception)}``",
                )
                raise NornirNautobotException()
            elif isinstance(exc.result.exception, jinja2.TemplateSyntaxError):
                logger.log_failure(
                    obj,
                    f"There was a jinja2.TemplateSyntaxError error: ``{str(exc.result.exception)}``",
                )
                raise NornirNautobotException()
            elif isinstance(exc.result.exception, jinja2.TemplateNotFound):
                logger.log_failure(
                    obj,
                    f"There was an issue finding the template and a jinja2.TemplateNotFound error was raised: ``{str(exc.result.exception)}``",
                )
                raise NornirNautobotException()
            elif isinstance(exc.result.exception, jinja2.TemplateError):
                logger.log_failure(obj, f"There was an issue general Jinja error: ``{str(exc.result.exception)}``")
                raise NornirNautobotException()
            raise

        make_folder(os.path.dirname(output_file_location))
        with open(output_file_location, "w") as filehandler:
            filehandler.write(filled_template)
        return Result(host=task.host, result={"config": filled_template})


class NetmikoNautobotNornirDriver(NautobotNornirDriver):
    """Default collection of Nornir Tasks based on Netmiko."""

    @staticmethod
    def get_config(task: Task, logger, obj, backup_file: str, remove_lines: list, substitute_lines: list) -> Result:
        """Get the latest configuration from the device using Netmiko.

        Args:
            task (Task): Nornir Task.
            logger (NornirLogger): Custom NornirLogger object to reflect job_results (via Nautobot Jobs) and Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            remove_lines (list): A list of regex lines to remove configurations.
            substitute_lines (list): A list of dictionaries with to remove and replace lines.

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        logger.log_debug(f"Executing get_config for {task.host.name} on {task.host.platform}")
        command = RUN_COMMAND_MAPPING.get(task.host.platform, RUN_COMMAND_MAPPING["default"])

        try:
            result = task.run(task=netmiko_send_command, command_string=command)
        except NornirSubTaskError as exc:
            if isinstance(exc.result.exception, NetmikoAuthenticationException):
                logger.log_failure(obj, f"Failed with an authentication issue: `{exc.result.exception}`")
                raise NornirNautobotException()

            if isinstance(exc.result.exception, NetmikoTimeoutException):
                logger.log_failure(obj, f"Failed with a timeout issue. `{exc.result.exception}`")
                raise NornirNautobotException()

            logger.log_failure(obj, f"Failed with an unknown issue. `{exc.result.exception}`")
            raise NornirNautobotException()

        if result[0].failed:
            return result

        running_config = result[0].result

        # Primarily seen in Cisco devices.
        if "ERROR: % Invalid input detected at" in running_config:
            logger.log_failure(obj, "Discovered `ERROR: % Invalid input detected at` in the output")
            raise NornirNautobotException()

        if remove_lines:
            logger.log_debug("Removing lines from configuration based on `remove_lines` definition")
            running_config = clean_config(running_config, remove_lines)
        if substitute_lines:
            logger.log_debug("Substitute lines from configuration based on `substitute_lines` definition")
            running_config = sanitize_config(running_config, substitute_lines)

        make_folder(os.path.dirname(backup_file))

        with open(backup_file, "w") as filehandler:
            filehandler.write(running_config)
        return Result(host=task.host, result={"config": running_config})
