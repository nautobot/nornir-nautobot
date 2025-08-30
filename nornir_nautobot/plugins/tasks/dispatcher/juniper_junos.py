"""nornir dispatcher for Juniper Junos."""
import os
from nornir_nautobot.plugins.tasks.dispatcher.default import NapalmDefault, NetmikoDefault
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import (
    netmiko_save_config,
    netmiko_send_config,
    netmiko_commit
)
from nornir_napalm.plugins.tasks import napalm_configure, napalm_confirm_commit

from nornir_nautobot.constants import EXCEPTION_TO_ERROR_MAPPER
from nornir_nautobot.exceptions import NornirNautobotException

from nornir_nautobot.utils.helpers import get_error_message

class NapalmJuniperJunos(NapalmDefault):
    """Collection of Napalm Nornir Tasks specific to Juniper JUNOS devices."""

    @classmethod
    def merge_config(  # pylint: disable=too-many-positional-arguments
        cls,
        task: Task,
        logger,
        obj,
        config: str,
        can_diff: bool = True,
    ) -> Result:
        """Send configuration to merge on the device.

        Args:
            task (Task): Nornir Task.
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            config (str): The config set.
            can_diff (bool): Whether to show the diff or not. Defaults to True.

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
            if not revert_in:
                task.run(task=napalm_confirm_commit)
        except NornirSubTaskError as exc:
            error_msg = error_msg = get_error_message("E1015", method="merge_config", exc=exc)
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)

        logger.info(
            f"result: {push_result[0].result}, changed: {push_result.changed}",
            extra={"object": obj},
        )

        if push_result.diff:
            if can_diff:
                logger.info(f"Diff:\n```\n_{push_result.diff}\n```", extra={"object": obj})
            else:
                logger.warning(
                    "Diff was requested but may include sensitive data. Ignoring...",
                    extra={"object": obj},
                )

        logger.info("Config merge ended", extra={"object": obj})
        return Result(host=task.host, result={"changed": push_result.changed, "result": push_result[0].result})


class NetmikoJuniperJunos(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to Juniper JUNOS devices."""

    @classmethod
    def merge_config(  # pylint: disable=too-many-positional-arguments
        cls,
        task: Task,
        logger,
        obj,
        config: str,
        can_diff: bool = True,
    ) -> Result:
        """Send configuration to merge on the device.

        Args:
            task (Task): Nornir Task.
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            config (str): The config set.
            can_diff (bool): Whether to show the diff or not. Defaults to True.

        Raises:
            NornirNautobotException: Authentication error.
            NornirNautobotException: Timeout error.
            NornirNautobotException: Other exception.

        Returns:
            Result: Nornir Result object with a dict as a result containing what changed and the result of the push.
        """
        logger.info("Config merge via netmiko starting", extra={"object": obj})
        try:
            push_result = task.run(
                task=netmiko_send_config,
                config_commands=config.splitlines(),
                enable=True,
            )
            task.run(task=netmiko_commit)
        except NornirSubTaskError as exc:
            error_code = EXCEPTION_TO_ERROR_MAPPER.get(type(exc.result.exception), "E1016")
            error_msg = get_error_message(error_code, exc=exc)
            logger.error(error_msg, extra={"object": obj})

        if push_result[0].failed:
            return push_result

        failed, error_msg = cls._has_hidden_errors(push_result[0].result)
        if failed:
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)

        logger.info(
            f"result: {push_result[0].result}, changed: {push_result[0].changed}",
            extra={"object": obj},
        )

        if push_result.diff:
            if can_diff:
                logger.info(f"Diff:\n```\n_{push_result.diff}\n```", extra={"object": obj})
            else:
                logger.warning(
                    "Diff was requested but may include sensitive data. Ignoring...",
                    extra={"object": obj},
                )

        logger.info("Config merge ended", extra={"object": obj})
        try:
            task.run(
                task=netmiko_save_config,
                confirm=True,
            )
        except NornirSubTaskError as exc:
            get_error_message("E1016", exc=exc)
            logger.error(error_msg, extra={"object": obj})
        return Result(host=task.host, result={"changed": push_result[0].changed, "result": push_result[0].result})
