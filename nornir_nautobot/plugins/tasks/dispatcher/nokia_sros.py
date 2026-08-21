"""nornir dispatcher for Nokia SROS."""

from __future__ import annotations

import inspect
import os
from typing import TYPE_CHECKING

import netmiko
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command

from nornir_nautobot.constants import (
    EXCEPTION_TO_ERROR_MAPPER,
)
from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.plugins.tasks.dispatcher.default import NetmikoDefault
from nornir_nautobot.utils.helpers import (
    get_error_message,
    get_stack_trace,
    is_truthy,
)

if TYPE_CHECKING:
    from inspect import MappingProxyType, Parameter
    from logging import Logger

    from nornir.core.task import MultiResult


class NetmikoNokiaSros(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to Nokia SROS devices."""

    setup_command = "environment no more"

    @classmethod
    def get_command(  # pylint: disable=too-many-positional-arguments,too-many-locals,too-many-arguments  # noqa: PLR0913, PLR0917
        cls,
        task: Task,
        logger: Logger,
        obj,
        command: str,
        command_file_path: str | None = None,
        force_offline: bool = False,
        **kwargs: dict[str, object],
    ) -> Result:
        """A tasks to get the commands from a device.

        Args:
            task (Task): Nornir Task.
            logger (Logger): Logger that may be a Nautobot Jobs or Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            command: A command to execute.
            command_file_path (str | None): The path to the command output file located in the Git repository.
            force_offline (bool): When True, read the output from ``command_file_path`` without consulting the
                device's ``offline_commands`` config context or custom field. Defaults to False.
            kwargs (dict[str, object]): Additional arguments to pass to the netmiko_send_command task.

        Returns:
            Result: Nornir Result containing command output keyed by the command string.

        Raises:
            NornirNautobotException: If command execution fails or the response contains hidden errors.
        """
        logger.debug(f"Executing get_command for {task.host.name} on {task.host.platform}")

        valid_params: MappingProxyType[str, Parameter] = inspect.signature(
            obj=netmiko.BaseConnection.send_command
        ).parameters
        allowed_kwargs: dict[str, object] = {
            netmiko_kwarg: netmiko_kwarg_value
            for netmiko_kwarg, netmiko_kwarg_value in cls._get_netmiko_kwargs(obj=obj).items()
            if netmiko_kwarg in valid_params
        }

        try:
            result: MultiResult = task.run(
                task=netmiko_send_command,
                command_string=cls.setup_command,
                enable=is_truthy(os.getenv("NORNIR_NAUTOBOT_NETMIKO_ENABLE_DEFAULT", default="False")),
                **kwargs,
                **allowed_kwargs,
            )
        except NornirSubTaskError as exc:
            error_msg = f"`E1020:` Session preparation failed. `{exc.result.exception}`"
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg) from exc

        use_offline: bool = force_offline or cls._offline_commands(obj=obj)
        try:
            if use_offline:
                result = task.run(
                    task=cls.get_git_command,
                    logger=logger,
                    command=command,
                    command_file_path=command_file_path,
                )
            else:
                result = task.run(
                    task=netmiko_send_command,
                    command_string=command,
                    enable=is_truthy(arg=os.getenv(key="NORNIR_NAUTOBOT_NETMIKO_ENABLE_DEFAULT", default="False")),
                    **kwargs,
                    **allowed_kwargs,
                )
                failed, error_msg = cls._has_hidden_errors(result_output=result[0].result)
                if failed:
                    logger.error(error_msg, extra={"object": obj})
                    raise NornirNautobotException(error_msg)
        except NornirSubTaskError as exc:
            error_code: str | None = EXCEPTION_TO_ERROR_MAPPER.get(key=type(exc.result.exception))
            kwargs = {"exc": exc, "error_code": error_code}
            if not error_code:
                kwargs["error_code"] = "E1014"
                kwargs["stack_trace"] = get_stack_trace(exc.result.exception)
            error_msg: str = get_error_message(**kwargs)
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg) from exc

        if use_offline:
            return Result(
                host=task.host, result={"output": {command: cls._parse_offline_output(raw_output=result[0].result)}}
            )
        return Result(host=task.host, result={"output": {command: result[0].result}})

    @classmethod
    def get_commands(  # pylint: disable=too-many-positional-arguments, too-many-locals
        cls,
        task: Task,
        logger: Logger,
        obj,
        command_list: list[str] | list[tuple[str, str]],
        **kwargs: dict[str, object],
    ) -> Result:
        """A tasks to get the commands from a device.

        Args:
            task (Task): Nornir Task.
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            command_list (list[str] | list[tuple[str, str]]):
                - In online mode (Netmiko), a list of command strings to execute on the device.
                - In offline mode (Git), a list of (command_label, file location) tuples
                  pointing to stored command output files in the Git repo.
            kwargs: Additional arguments to pass to the netmiko_send_command task.

        Returns:
            Result: Nornir Result containing command outputs keyed by command.

        Raises:
            NornirNautobotException: If command execution fails or the response contains hidden errors.
        """
        logger.debug(f"Executing get_commands for {task.host.name} on {task.host.platform}")
        valid_params: MappingProxyType[str, Parameter] = inspect.signature(
            obj=netmiko.BaseConnection.send_command
        ).parameters
        allowed_kwargs: dict[str, object] = {
            netmiko_kwarg: netmiko_kwarg_value
            for netmiko_kwarg, netmiko_kwarg_value in cls._get_netmiko_kwargs(obj=obj).items()
            if netmiko_kwarg in valid_params
        }

        try:
            result: MultiResult = task.run(
                task=netmiko_send_command,
                command_string=cls.setup_command,
                enable=is_truthy(os.getenv("NORNIR_NAUTOBOT_NETMIKO_ENABLE_DEFAULT", default="False")),
                **kwargs,
                **allowed_kwargs,
            )
        except NornirSubTaskError as exc:
            error_msg = f"`E1020:` Session preparation failed. `{exc.result.exception}`"
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg) from exc

        command_results: dict[str, object] = {}
        for command in command_list:
            try:
                if cls._offline_commands(obj=obj):
                    command, *rest = command
                    command_file_path: str | None = rest[0] if rest else None
                    result: MultiResult = task.run(
                        task=cls.get_git_command,
                        logger=logger,
                        command=command,
                        command_file_path=command_file_path,
                    )
                else:
                    result: MultiResult = task.run(
                        task=netmiko_send_command,
                        command_string=command,
                        enable=is_truthy(arg=os.getenv(key="NORNIR_NAUTOBOT_NETMIKO_ENABLE_DEFAULT", default="False")),
                        **kwargs,
                        **allowed_kwargs,
                    )
                    failed, error_msg = cls._has_hidden_errors(result_output=result[0].result)
                    if failed:
                        logger.error(error_msg, extra={"object": obj})
                        raise NornirNautobotException(error_msg)
                if cls._offline_commands(obj=obj):
                    command_results.update({command: cls._parse_offline_output(raw_output=result[0].result)})
                else:
                    command_results.update({command: result[0].result})
            except NornirSubTaskError as exc:
                error_code: str | None = EXCEPTION_TO_ERROR_MAPPER.get(key=type(exc.result.exception))
                kwargs = {"exc": exc, "error_code": error_code}
                if not error_code:
                    kwargs["error_code"] = "E1014"
                    kwargs["stack_trace"] = get_stack_trace(exc=exc.result.exception)
                error_msg: str = get_error_message(**kwargs)
                logger.error(error_msg, extra={"object": obj})
                raise NornirNautobotException(error_msg) from exc

        return Result(host=task.host, result={"output": command_results})
