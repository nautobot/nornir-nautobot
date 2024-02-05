"""nornir dispatcher for Ruckus ICX/FastIron Switches."""

from nornir.core.task import Result, Task
from nornir.core.exceptions import NornirSubTaskError

from nornir_netmiko.tasks import netmiko_save_config, netmiko_send_config
from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.plugins.tasks.dispatcher.default import NetmikoDefault


class NetmikoRuckusFastiron(NetmikoDefault):
    """Driver for Ruckus ICX/FastIron Switches."""

    config_command = "show running-config"

    @staticmethod
    def merge_config(task: Task, logger, obj, config: str) -> Result:
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
        logger.info("Config merge starting", extra={"object": obj})

        try:
            config_list = config.splitlines()
            push_result = task.run(
                task=netmiko_send_config,
                config_commands=config_list,
            )
        except NornirSubTaskError as exc:
            error_msg = f"Failed with error: `{exc.result.exception}`"
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
        try:
            save_result = task.run(
                task=netmiko_save_config,
            )
            logger.info(f"config saved: {save_result[0].result}", extra={"object": obj})
        except NornirSubTaskError as exc:
            error_msg = f"`E1027:` config merged, but failed to save: {exc.result.exception}"
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg) from exc
        push_result[0].changed = True

        return Result(
            host=task.host,
            result={
                "changed": push_result[0].changed,
                "result": push_result[0].result,
                "failed": push_result[0].failed,
            },
        )
