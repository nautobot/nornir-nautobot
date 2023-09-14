"""default driver for the network_importer."""
# pylint: disable=raise-missing-from,too-many-arguments

import logging
import os
import socket
from typing import Optional

import jinja2

try:
    from netmiko.ssh_exception import NetmikoAuthenticationException, NetmikoTimeoutException
except ImportError:
    from netmiko import NetmikoAuthenticationException, NetmikoTimeoutException

from netutils.config.clean import clean_config, sanitize_config
from netutils.config.compliance import compliance
from netutils.dns import is_fqdn_resolvable
from netutils.ip import is_ip
from netutils.ping import tcp_ping
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import Result, Task
from nornir_jinja2.plugins.tasks import template_file
from nornir_napalm.plugins.tasks import napalm_get, napalm_configure
from nornir_netmiko.tasks import netmiko_send_command

from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.utils.helpers import make_folder


_logger = logging.getLogger(__name__)


class NautobotNornirDriver:
    """Default collection of Nornir Tasks based on Napalm."""

    config_command = "show run"

    @classmethod
    def get_config(
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

        # TODO: Find standard napalm exceptions and account for them
        try:
            result = task.run(task=napalm_get, getters=["config"], retrieve="running")
        except NornirSubTaskError as exc:
            logger.log_failure(obj, f"`get_config` method failed with an unexpected issue: `{exc.result.exception}`")
            raise NornirNautobotException(
                "`get_config` method failed with an unexpected issue: `{exc.result.exception}`"
            )

        if result[0].failed:
            logger.log_failure(
                obj, f"`get_config` nornir task failed with an unexpected issue: `{str(result.exception)}`"
            )
            return result

        running_config = result[0].result.get("config", {}).get("running", None)
        if remove_lines:
            logger.log_debug("Removing lines from configuration based on `remove_lines` definition")
            running_config = clean_config(running_config, remove_lines)

        if substitute_lines:
            logger.log_debug("Substitute lines from configuration based on `substitute_lines` definition")
            running_config = sanitize_config(running_config, substitute_lines)

        if backup_file:
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
                raise NornirNautobotException("There was not an IP or resolvable, preemptively failed.")
            ip_addr = socket.gethostbyname(task.host.hostname)

        # TODO: Allow port to be configurable
        port = 22
        if not tcp_ping(ip_addr, port):
            logger.log_failure(obj, f"Could not connect to IP: {ip_addr} and port: {port}, preemptively failed.")
            raise NornirNautobotException(f"Could not connect to IP: {ip_addr} and port: {port}, preemptively failed.")
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
            logger (NornirLogger): Custom NornirLogger object to reflect job results (via Nautobot Jobs) and Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            features (dict): A dictionary describing the configurations required.
            backup_file (str): The file location of where the back configuration should be saved.
            intended_file (str):  The file location of where the intended configuration should be saved.
            platform (str): The platform slug of the device.

        Returns:
            Result: Nornir Result object with a feature_data key of the compliance data.
        """
        if not os.path.exists(backup_file):
            logger.log_failure(obj, f"Backup file Not Found at location: `{backup_file}`, preemptively failed.")
            raise NornirNautobotException(f"Backup file Not Found at location: `{backup_file}`, preemptively failed.")

        if not os.path.exists(intended_file):
            logger.log_failure(
                obj, f"Intended config file NOT Found at location: `{intended_file}`, preemptively failed."
            )
            raise NornirNautobotException(
                f"Intended config file NOT Found at location: `{intended_file}`, preemptively failed."
            )

        try:
            feature_data = compliance(features, backup_file, intended_file, platform)
        except Exception as error:  # pylint: disable=broad-except
            logger.log_failure(obj, f"UNKNOWN Failure of: {str(error)}")
            raise NornirNautobotException(f"UNKNOWN Failure of: {str(error)}")
        return Result(host=task.host, result={"feature_data": feature_data})

    @staticmethod
    def generate_config(
        task: Task,
        logger,
        obj,
        jinja_template: str,
        jinja_root_path: str,
        output_file_location: str,
        jinja_filters: Optional[dict] = None,
        jinja_env: Optional[jinja2.Environment] = None,
    ) -> Result:
        """A small wrapper around template_file Nornir task.

        Args:
            task (Task): Nornir Task.
            logger (NornirLogger): Custom NornirLogger object to reflect job results (via Nautobot Jobs) and Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            jinja_template (str): The file location of the actual Jinja template.
            jinja_root_path (str): The file folder where the file will be saved to.
            jinja_filters (dict): The filters which will be added to the jinja2 environment.
            jinja_env (jinja2.Environment): The jinja2 environment to use. If not provided, nornir will create one.
            output_file_location (str): The filename where the file will be saved to.

        Returns:
            Result: Nornir Result object.
        """
        try:
            filled_template = task.run(
                **task.host,
                task=template_file,
                template=jinja_template,
                path=jinja_root_path,
                jinja_filters=jinja_filters,
                jinja_env=jinja_env,
            )[0].result
        except NornirSubTaskError as exc:
            if isinstance(exc.result.exception, jinja2.exceptions.UndefinedError):  # pylint: disable=no-else-raise
                logger.log_failure(
                    obj,
                    f"There was a jinja2.exceptions.UndefinedError error: ``{str(exc.result.exception)}``",
                )
                raise NornirNautobotException(
                    f"There was a jinja2.exceptions.UndefinedError error: ``{str(exc.result.exception)}``"
                )
            elif isinstance(exc.result.exception, jinja2.TemplateSyntaxError):
                logger.log_failure(
                    obj,
                    f"There was a jinja2.TemplateSyntaxError error: ``{str(exc.result.exception)}``",
                )
                raise NornirNautobotException(
                    f"There was a jinja2.TemplateSyntaxError error: ``{str(exc.result.exception)}``"
                )
            elif isinstance(exc.result.exception, jinja2.TemplateNotFound):
                logger.log_failure(
                    obj,
                    f"There was an issue finding the template and a jinja2.TemplateNotFound error was raised: ``{str(exc.result.exception)}``",
                )
                raise NornirNautobotException(
                    f"There was an issue finding the template and a jinja2.TemplateNotFound error was raised: ``{str(exc.result.exception)}``"
                )
            elif isinstance(exc.result.exception, jinja2.TemplateError):
                logger.log_failure(obj, f"There was an issue general Jinja error: ``{str(exc.result.exception)}``")
                raise NornirNautobotException(
                    f"There was an issue general Jinja error: ``{str(exc.result.exception)}``"
                )
            raise

        make_folder(os.path.dirname(output_file_location))
        with open(output_file_location, "w", encoding="utf8") as filehandler:
            filehandler.write(filled_template)
        return Result(host=task.host, result={"config": filled_template})

    @staticmethod
    def _remove_lines(logger, _running_config: str, remove_lines: list) -> str:
        """Removes lines in configuration as specified in Remove Lines list.

        Args:
            logger (NornirLogger): Custom NornirLogger object to reflect job results (via Nautobot Jobs) and Python logger.
            _running_config (str): a device running configuration.
            remove_lines (list): A list of regex lines to remove configurations.

        Returns:
            Result: Clean running configuration if remove lines set.
        """
        if not remove_lines:
            return _running_config
        logger.log_debug("Removing lines from configuration based on `remove_lines` definition")
        return clean_config(_running_config, remove_lines)

    @staticmethod
    def _substitute_lines(logger, _running_config: str, substitute_lines: list) -> str:
        """Substitutes lines in configuration as specified in substitute Lines list.

        Args:
            logger (NornirLogger): Custom NornirLogger object to reflect job results (via Nautobot Jobs) and Python logger.
            _running_config (str): a device running configuration.
            substitute_lines (list): A list of dictionaries with to remove and replace lines.

        Returns:
            Result: running configuration with substitutions.
        """
        if not substitute_lines:
            return _running_config
        logger.log_debug("Substitute lines from configuration based on `substitute_lines` definition")
        return sanitize_config(_running_config, substitute_lines)

    @staticmethod
    def _save_file(logger, backup_file: str, _running_config: str) -> None:
        """Saves Running Configuration to a specified file.

        Args:
            logger (NornirLogger): Custom NornirLogger object to reflect job results (via Nautobot Jobs) and Python logger.
            _running_config (str): a device running configuration.
            backup_file (str): String representing backup file path.

        Returns:
            Result: Running Config is saved into backup file path.
        """
        make_folder(os.path.dirname(backup_file))
        logger.log_debug(f"Saving Configuration to file: {backup_file}")
        with open(backup_file, "w", encoding="utf8") as filehandler:
            filehandler.write(_running_config)

    def provision_config(self, *args, **kwargs):
        """This method is being deprecated. Please use replace_config instead."""
        _logger.warning(
            "WARNING: The method 'provision_config()' will be removed in the next major release. Please use 'replace_config()' instead."
        )
        return self.replace_config(*args, **kwargs)

    @staticmethod
    def replace_config(
        task: Task,
        logger,
        obj,
        config: str,
    ) -> Result:
        """Push candidate configuration to the device.

        Args:
            task (Task): Nornir Task.
            logger (NornirLogger): Custom NornirLogger object to reflect job_results (via Nautobot Jobs) and Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            config (str): The candidate config.

        Raises:
            NornirNautobotException: Authentication error.
            NornirNautobotException: Timeout error.
            NornirNautobotException: Other exception.

        Returns:
            Result: Nornir Result object with a dict as a result containing what changed and the result of the push.
        """
        logger.log_success(obj, "Config provision starting")
        # Sending None to napalm_configure for revert_in will disable it, so we don't want a default value.
        revert_in = os.getenv("NORNIR_NAUTOBOT_REVERT_IN_SECONDS")
        if revert_in is not None:
            revert_in = int(revert_in)

        try:
            push_result = task.run(
                task=napalm_configure,
                configuration=config,
                replace=True,
                revert_in=revert_in,
            )
        except NornirSubTaskError as exc:
            logger.log_failure(obj, f"Failed with an unknown issue. `{exc.result.exception}`")
            raise NornirNautobotException()

        logger.log_success(obj, f"result: {push_result[0].result}, changed: {push_result.changed}")
        logger.log_success(obj, "Config provision ended")
        return Result(host=task.host, result={"changed": push_result.changed, "result": push_result[0]})

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
        logger.log_success(obj, "Config merge starting")
        # Sending None to napalm_configure for revert_in will disable it, so we don't want a default value.
        revert_in = os.getenv("NORNIR_NAUTOBOT_REVERT_IN_SECONDS")
        if revert_in is not None:
            revert_in = int(revert_in)

        try:
            push_result = task.run(
                task=napalm_configure,
                configuration=config,
                replace=False,
                revert_in=revert_in,
            )
        except NornirSubTaskError as exc:
            logger.log_failure(obj, f"Failed with an unknown issue. `{exc.result.exception}`")
            raise NornirNautobotException()

        logger.log_success(obj, f"result: {push_result[0].result}, changed: {push_result.changed}")
        logger.log_success(obj, "Config merge ended")
        return Result(host=task.host, result={"changed": push_result.changed, "result": push_result[0]})


class NetmikoNautobotNornirDriver(NautobotNornirDriver):
    """Default collection of Nornir Tasks based on Netmiko."""

    config_command = "show run"

    @classmethod
    def get_config(
        cls, task: Task, logger, obj, backup_file: str, remove_lines: list, substitute_lines: list
    ) -> Result:
        """Get the latest configuration from the device using Netmiko.

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
        logger.log_debug(f"Executing get_config for {task.host.name} on {task.host.platform}")
        command = cls.config_command

        try:
            result = task.run(task=netmiko_send_command, command_string=command)
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

        running_config = result[0].result

        # Primarily seen in Cisco devices.
        if "ERROR: % Invalid input detected at" in running_config:
            logger.log_failure(obj, "Discovered `ERROR: % Invalid input detected at` in the output")
            raise NornirNautobotException("Discovered `ERROR: % Invalid input detected at` in the output")

        if remove_lines:
            logger.log_debug("Removing lines from configuration based on `remove_lines` definition")
            running_config = clean_config(running_config, remove_lines)
        if substitute_lines:
            logger.log_debug("Substitute lines from configuration based on `substitute_lines` definition")
            running_config = sanitize_config(running_config, substitute_lines)

        if backup_file:
            make_folder(os.path.dirname(backup_file))

            with open(backup_file, "w", encoding="utf8") as filehandler:
                filehandler.write(running_config)
        return Result(host=task.host, result={"config": running_config})
