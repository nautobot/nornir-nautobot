"""default driver for the network_importer."""

# pylint: disable=raise-missing-from,too-many-arguments

import logging
import os
import socket
from typing import Optional

import jinja2

from netutils.config.clean import clean_config, sanitize_config
from netutils.config.compliance import compliance
from netutils.dns import is_fqdn_resolvable
from netutils.ip import is_ip
from netutils.ping import tcp_ping

from netmiko import NetmikoAuthenticationException, NetmikoTimeoutException

from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import Result, Task

from nornir_jinja2.plugins.tasks import template_file
from nornir_napalm.plugins.tasks import napalm_configure, napalm_get
from nornir_netmiko.tasks import netmiko_send_command

from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.utils.helpers import make_folder

_logger = logging.getLogger(__name__)


class DispatcherMixin:
    """Mixin for non-network driver related tasks."""

    tcp_port = 22

    @classmethod
    def _get_hostname(cls, task: Task, obj=None) -> str:  # pylint: disable=unused-argument
        return task.host.hostname

    @classmethod
    def _get_tcp_port(cls, obj) -> str:
        custom_field = obj.cf.get("tcp_port")
        if isinstance(custom_field, int):
            return custom_field
        config_context = obj.get_config_context().get("tcp_port")
        if isinstance(config_context, int):
            return config_context
        return cls.tcp_port

    @classmethod
    def check_connectivity(cls, task: Task, logger, obj) -> Result:
        """Check the connectivity to a network device.

        Args:
            task (Task): Nornir Task.
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.

        Returns:
            Result: Nornir Result object.
        """
        hostname = cls._get_hostname(task)
        if is_ip(hostname):
            ip_addr = hostname
        else:
            if not is_fqdn_resolvable(hostname):
                error_msg = (
                    f"`E1003:` The hostname {hostname} did not have an IP nor was resolvable, preemptively failed."
                )
                logger.error(error_msg, extra={"object": obj})
                raise NornirNautobotException(error_msg)
            ip_addr = socket.gethostbyname(hostname)

        port = cls._get_tcp_port(obj)
        # TODO: Remove after fixing tcp_ping in netutils
        try:
            _tcp_ping = tcp_ping(ip_addr, port)
        except socket.error:
            _tcp_ping = False
        if not _tcp_ping:
            error_msg = f"`E1004:` Could not connect to IP: `{ip_addr}` and port: `{port}`, preemptively failed."
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)
        if not task.host.username:
            error_msg = "`E1005:` There was no username defined, preemptively failed."
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)
        if not task.host.password:
            error_msg = "`E1006:` There was no password defined, preemptively failed."
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)

        return Result(host=task.host)

    @classmethod
    def compliance_config(
        cls,
        task: Task,
        logger,
        obj,
        features: str,
        backup_file: str,
        intended_file: str,
        platform: str,
    ) -> Result:
        """Compare two configurations against each other.

        Args:
            task (Task): Nornir Task.
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            features (dict): A dictionary describing the configurations required.
            backup_file (str): The file location of where the back configuration should be saved.
            intended_file (str):  The file location of where the intended configuration should be saved.
            platform (str): The platform network_driver of the device.

        Returns:
            Result: Nornir Result object with a feature_data key of the compliance data.
        """
        if not os.path.exists(backup_file):
            error_msg = f"`E1007:` Backup file Not Found at location: `{backup_file}`, preemptively failed."
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)

        if not os.path.exists(intended_file):
            error_msg = f"`E1008:` Intended config file NOT Found at location: `{intended_file}`, preemptively failed."
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)

        try:
            feature_data = compliance(features, backup_file, intended_file, platform)
        except Exception as error:  # pylint: disable=broad-except
            error_msg = f"`E1009:` UNKNOWN Failure of: {str(error)}"
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)
        return Result(host=task.host, result={"feature_data": feature_data})

    @classmethod
    def generate_config(
        cls,
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
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
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
                error_msg = (
                    f"`E1010:` There was a jinja2.exceptions.UndefinedError error: ``{str(exc.result.exception)}``"
                )
                logger.error(error_msg, extra={"object": obj})
                raise NornirNautobotException(error_msg)

            elif isinstance(exc.result.exception, jinja2.TemplateSyntaxError):
                error_msg = (f"`E1011:` There was a jinja2.TemplateSyntaxError error: ``{str(exc.result.exception)}``",)
                logger.error(error_msg, extra={"object": obj})
                raise NornirNautobotException(error_msg)

            elif isinstance(exc.result.exception, jinja2.TemplateNotFound):
                error_msg = f"`E1012:` There was an issue finding the template and a jinja2.TemplateNotFound error was raised: ``{str(exc.result.exception)}``"
                logger.error(error_msg, extra={"object": obj})
                raise NornirNautobotException(error_msg)

            elif isinstance(exc.result.exception, jinja2.TemplateError):
                error_msg = f"`E1013:` There was an issue general Jinja error: ``{str(exc.result.exception)}``"
                logger.error(error_msg, extra={"object": obj})
                raise NornirNautobotException(error_msg)

            error_msg = f"`E1014:` Failed with an unknown issue. `{exc.result.exception}`"
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)

        make_folder(os.path.dirname(output_file_location))
        with open(output_file_location, "w", encoding="utf8") as filehandler:
            filehandler.write(filled_template)
        return Result(host=task.host, result={"config": filled_template})

    @classmethod
    def _remove_lines(cls, logger, _running_config: str, remove_lines: list) -> str:
        """Removes lines in configuration as specified in Remove Lines list.

        Args:
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            _running_config (str): a device running configuration.
            remove_lines (list): A list of regex lines to remove configurations.

        Returns:
            Result: Clean running configuration if remove lines set.
        """
        if not remove_lines:
            return _running_config
        logger.debug("Removing lines from configuration based on `remove_lines` definition")
        return clean_config(_running_config, remove_lines)

    @classmethod
    def _substitute_lines(cls, logger, _running_config: str, substitute_lines: list) -> str:
        """Substitutes lines in configuration as specified in substitute Lines list.

        Args:
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            _running_config (str): a device running configuration.
            substitute_lines (list): A list of dictionaries with to remove and replace lines.

        Returns:
            Result: running configuration with substitutions.
        """
        if not substitute_lines:
            return _running_config
        logger.debug("Substitute lines from configuration based on `substitute_lines` definition")
        return sanitize_config(_running_config, substitute_lines)

    @classmethod
    def _save_file(cls, logger, backup_file: str, _running_config: str) -> None:
        """Saves Running Configuration to a specified file.

        Args:
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            _running_config (str): a device running configuration.
            backup_file (str): String representing backup file path.

        Returns:
            Result: Running Config is saved into backup file path.
        """
        make_folder(os.path.dirname(backup_file))
        logger.debug(f"Saving Configuration to file: {backup_file}")
        with open(backup_file, "w", encoding="utf8") as filehandler:
            filehandler.write(_running_config)


class NapalmDefault(DispatcherMixin):
    """Default collection of Nornir Tasks based on Napalm."""

    @classmethod
    def get_config(
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

        # TODO: Find standard napalm exceptions and account for them
        try:
            result = task.run(task=napalm_get, getters=["config"], retrieve="running")
        except NornirSubTaskError as exc:
            error_msg = f"`E1015:` `get_config` method failed with an unexpected issue: `{exc.result.exception}`"
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)

        if result[0].failed:
            # TODO: investigate this, is there a better way to handle? recursive function?
            logger.error(
                f"`get_config` nornir task failed with an unexpected issue: `{str(result.exception)}`",
                extra={"object": obj},
            )
            return result

        running_config = result[0].result.get("config", {}).get("running", None)
        if remove_lines:
            logger.debug("Removing lines from configuration based on `remove_lines` definition")
            running_config = clean_config(running_config, remove_lines)

        if substitute_lines:
            logger.debug("Substitute lines from configuration based on `substitute_lines` definition")
            running_config = sanitize_config(running_config, substitute_lines)

        if backup_file:
            make_folder(os.path.dirname(backup_file))

            with open(backup_file, "w", encoding="utf8") as filehandler:
                filehandler.write(running_config)
        return Result(host=task.host, result={"config": running_config})

    @classmethod
    def replace_config(
        cls,
        task: Task,
        logger,
        obj,
        config: str,
    ) -> Result:
        """Push candidate configuration to the device.

        Args:
            task (Task): Nornir Task.
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            config (str): The candidate config.

        Raises:
            NornirNautobotException: Authentication error.
            NornirNautobotException: Timeout error.
            NornirNautobotException: Other exception.

        Returns:
            Result: Nornir Result object with a dict as a result containing what changed and the result of the push.
        """
        logger.info("Config provision starting", extra={"object": obj})
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
            error_msg = f"`E1015:` Failed with an unknown issue. `{exc.result.exception}`"
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)

        logger.info(
            f"result: {push_result[0].result}, changed: {push_result.changed}",
            extra={"object": obj},
        )
        logger.info("Config provision ended", extra={"object": obj})
        return Result(
            host=task.host,
            result={"changed": push_result.changed, "result": push_result[0].result},
        )

    @classmethod
    def merge_config(
        cls,
        task: Task,
        logger,
        obj,
        config: str,
    ) -> Result:
        """Send configuration to merge on the device.

        Args:
            task (Task): Nornir Task.
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            config (str): The config set.

        Raises:
            NornirNautobotException: Authentication error.
            NornirNautobotException: Timeout error.
            NornirNautobotException: Other exception.

        Returns:
            Result: Nornir Result object with a dict as a result containing what changed and the result of the push.
        """
        logger.info("Config merge starting", extra={"object": obj})
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
            error_msg = f"`E1015:` Failed with an unknown issue. `{exc.result.exception}`"
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)

        logger.info(
            f"result: {push_result[0].result}, changed: {push_result.changed}",
            extra={"object": obj},
        )

        if push_result.diff:
            logger.info(f"Diff:\n```\n_{push_result.diff}\n```", extra={"object": obj})

        logger.info("Config merge ended", extra={"object": obj})
        return Result(
            host=task.host,
            result={"changed": push_result.changed, "result": push_result[0].result},
        )


class NetmikoDefault(DispatcherMixin):
    """Default collection of Nornir Tasks based on Netmiko."""

    config_command = "show run"

    @classmethod
    def get_config(
        cls,
        task: Task,
        logger,
        obj,
        backup_file: str,
        remove_lines: list,
        substitute_lines: list,
    ) -> Result:
        """Get the latest configuration from the device using Netmiko.

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
        logger.debug(f"Executing get_config for {task.host.name} on {task.host.platform}")
        command = cls.config_command

        try:
            result = task.run(task=netmiko_send_command, command_string=command)
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

        running_config = result[0].result

        # Primarily seen in Cisco devices.
        if "ERROR: % Invalid input detected at" in running_config:
            error_msg = "`E1019:` Discovered `ERROR: % Invalid input detected at` in the output"
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)

        if remove_lines:
            logger.debug("Removing lines from configuration based on `remove_lines` definition")
            running_config = clean_config(running_config, remove_lines)
        if substitute_lines:
            logger.debug("Substitute lines from configuration based on `substitute_lines` definition")
            running_config = sanitize_config(running_config, substitute_lines)

        if backup_file:
            make_folder(os.path.dirname(backup_file))

            with open(backup_file, "w", encoding="utf8") as filehandler:
                filehandler.write(running_config)
        return Result(host=task.host, result={"config": running_config})
