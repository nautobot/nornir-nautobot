"""default network_importer driver for Juniper."""

from .default import NautobotNornirDriver as DefaultNautobotNornirDriver
import routeros_api
import os
import json
import socket
from typing import Optional
import jinja2
from .platform_settings.api_schemas import mikrotik_resources
from deepdiff import DeepDiff
from netutils.config.clean import clean_config, sanitize_config
from netutils.config.compliance import compliance
from netutils.dns import is_fqdn_resolvable
from netutils.ip import is_ip
from netutils.ping import tcp_ping
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import Result, Task
from nornir_jinja2.plugins.tasks import template_file

from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.utils.helpers import make_folder

class NautobotNornirDriver(DefaultNautobotNornirDriver):
    """Default collection of Nornir Tasks based on Napalm."""

    @staticmethod
    def get_config(task: Task, logger, obj, backup_file: str, remove_lines: list, substitute_lines: list) -> Result:
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
        connection = routeros_api.RouterOsApiPool(  # inventory, secrets to be integrated
            obj.primary_ip4.host, username=task.host.username, password=task.host.password, plaintext_login=True
        )
        config_data = {}
        api = connection.get_api()

        for mikrotik_resource in mikrotik_resources:
            try:
                resource = api.get_resource(mikrotik_resource["endpoint"])
                config_data[mikrotik_resource["endpoint"]] = resource.get()
            except:
                logger.log_failure(obj, f"`get_config` method failed with an unexpected issue: `{Exception.NameError}`")
                raise NornirNautobotException(
                f"`get_config` method failed with an unexpected issue: `{Exception}`"
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
                raise NornirNautobotException("There was not an IP or resolvable, preemptively failed.")
            ip_addr = socket.gethostbyname(task.host.hostname)

        # TODO: Allow port to be configurable, allow ssl as well
        port = 8728
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
            intended_config = json.loads(intended_file)
        except Exception as error:
            logger.log_failure(obj, f"UNKNOWN Failure of: {str(error)}")
            raise NornirNautobotException(f"Failed to open intended config File: {str(error)}")

        try:
            backup_config = json.loads(backup_file)
        except Exception as error:
            logger.log_failure(obj, f"UNKNOWN Failure of: {str(error)}")
            raise NornirNautobotException(f"Failed to open backup config File: {str(error)}")         

        cleaned_intended = {
            mikrotik_resource["endpoint"]: [
                {k: v for k, v in item.items() if k in mikrotik_resource["keys"]}
                for item in intended_config.get(mikrotik_resource["endpoint"], [])
            ]
            for mikrotik_resource in mikrotik_resources
        }

        cleaned_backup = {
            mikrotik_resource["endpoint"]: [
                {k: v for k, v in item.items() if k in mikrotik_resource["keys"]}
                for item in backup_config.get(mikrotik_resource["endpoint"], [])
            ]
            for mikrotik_resource in mikrotik_resources
        }

        compliance_rules = [feature["name"] for feature in features]
        feature_data = dict.fromkeys(compliance_rules)
        try:
            for mikrotik_resource in mikrotik_resources:
                if mikrotik_resource["compliance_rule_name"] in feature_data.keys():
                    feature_intended = cleaned_intended[mikrotik_resource["endpoint"]]
                    feature_backup = cleaned_backup[mikrotik_resource["endpoint"]]
                    ddiff = DeepDiff(feature_intended, feature_backup, ignore_order=True)
                    feature_data[mikrotik_resource["compliance_rule_name"]] = {
                        'actual': feature_backup,
                        'cannot_parse': True,
                        'compliant': True if ddiff == {} else False,
                        'extra': ddiff.get("iterable_item_added", {}),
                        'intended': feature_intended,
                        'missing': ddiff.get("iterable_item_removed", {}),
                        'ordered_compliant': True,
                        'unordered_compliant': True,
                     }
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
    ) -> Result:
        """A small wrapper around template_file Nornir task.

        Args:
            task (Task): Nornir Task.
            logger (NornirLogger): Custom NornirLogger object to reflect job results (via Nautobot Jobs) and Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            jinja_template (str): The file location of the actual Jinja template.
            jinja_root_path (str): The file folder where the file will be saved to.
            jinja_filters (dict): The filters which will be added to the jinja2 environment.
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
