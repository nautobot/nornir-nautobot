"""network_importer driver for Ruckus ICX/FastIron Switches."""
from nornir.core.task import Result, Task
from nornir.core.exceptions import NornirSubTaskError

from nornir_netmiko.tasks import netmiko_save_config, netmiko_send_config
from nornir_nautobot.exceptions import NornirNautobotException

from .default import NetmikoNautobotNornirDriver as DefaultNautobotNornirDriver


class NautobotNornirDriver(DefaultNautobotNornirDriver):
    """Driver for Ruckus ICX/FastIron Switches."""

    config_command = "show running-config"

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
        NETMIKO_FAIL_MSG = ["invalid", "fail"]  # pylint: disable=C0103
        logger.log_success(obj, "Config merge starting")

        try:
            config_list = config.splitlines()
            push_result = task.run(
                task=netmiko_send_config,
                config_commands=config_list,
            )
        except NornirSubTaskError as exc:
            logger.log_failure(obj, f"Failed with error: `{exc.result.exception}`")
            raise NornirNautobotException() from exc

        if any(msg in push_result[0].result.lower() for msg in NETMIKO_FAIL_MSG):
            logger.log_warning(obj, "Config merged with errors, please check full info log below.")
            logger.log_failure(obj, f"result: {push_result[0].result}")
            push_result[0].failed = True
        else:
            logger.log_success(obj, "Config merged successfully.")
            logger.log_info(obj, f"result: {push_result[0].result}")
            push_result[0].failed = False
            try:
                save_result = task.run(
                    task=netmiko_save_config,
                )
                logger.log_info(obj, f"config saved: {save_result[0].result}")
            except NornirSubTaskError as exc:
                logger.log_failure(obj, f"config merged, but failed to save: {exc.result.exception}")
        push_result[0].changed = True

        return Result(
            host=task.host,
            result={
                "changed": push_result[0].changed,
                "result": push_result[0].result,
                "failed": push_result[0].failed,
            },
        )
