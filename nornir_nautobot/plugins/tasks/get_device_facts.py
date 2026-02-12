"""Getter for SSH commands."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from jsonschema import ValidationError
from jsonschema import validate as validate_jsonschema
from nornir.core.task import Result, Task

from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.plugins.tasks.dispatcher import dispatcher
from nornir_nautobot.utils.formatter import perform_data_extraction
from nornir_nautobot.utils.helpers import (
    _get_elements_to_run,
    _parse_command_result,
    _validate_platform_parsing_info,
    get_error_message,
)


@dataclass
class Section:
    """Defines a section with a command mapper YAML file.

    Section is identified a name, has a schema, and might have excluded sub-sections.
    """

    name: str  # mandatory
    schema: Optional[str] = None  # optional string
    exclude: List[str] = field(default_factory=list)  # optional list of strings


def get_device_facts(
    task: Task,
    command_specifications: Dict,
    section_instructions: List[Section],
    jinja_env,
    logger,
    framework,
    parsing_kwargs,
    *args,
    **kwargs,
):  # pylint: disable=too-many-arguments,too-many-positional-arguments,unused-argument,too-many-locals
    """Run platform-specific commands with parsing and logging.

    Args:
        task: Nornir Task object.
        command_specifications: Dictionary of command specifications. (All YAML files content.)
        section_instructions: List of Section instances. (Specify what to include, exclude and schema for validation)
        jinja_env: A fully configured jinja2 environment
        logger: Logger object to use for logging.
        framework: The framework to use for the dispatcher E.g. "netmiko".
        parsing_kwargs: Dictionary with parsing information (attributes).
        *args: Additional positional arguments to pass to the method.
        **kwargs: Additional keyword arguments to pass to the method.

    Returns:
        Result: Nornir Task result object.
    """
    # Inventory based facts (pre-defined or discovered)
    facts = {
        "sync_driver": {
            "platform": task.host.platform,
            "manufacturer": task.host.platform.split("_")[0].title() if task.host.platform else "",
        }
    }

    for section in section_instructions:
        # ---- 1. Command Execution & Parsing -------------------------------------
        _validate_platform_parsing_info(task, command_specifications, section.name)
        commands = _get_elements_to_run(
            yaml_parsed_info=command_specifications[task.host.platform][section.name],
            skip_list=section.exclude,
        )
        logger.debug(f"Commands to run: {[cmd['command'] for cmd in commands]}")

        # ---- 2. Command Execution & Parsing -------------------------------------
        try:
            commands_result = task.run(
                task=dispatcher,
                method="get_commands",
                logger=logger,
                obj=task.host.data["obj"],
                framework=framework,
                command_list=[command["command"] for command in commands],
            )[1].result["output"]
        except NornirNautobotException as exc:
            error_msg = get_error_message("E1037", hostname=task.host.name)
            logger.error(error_msg)
            return Result(host=task.host, result=error_msg, failed=True, exception=exc)

        # pylint: disable=broad-exception-caught
        try:
            preformatted_facts = {
                cmd["command"]: _parse_command_result(
                    network_driver=task.host.platform,
                    command=cmd["command"],
                    raw_output=commands_result[cmd["command"]],
                    parser_type=cmd.get("parser"),
                    logger=logger,
                    parsing_kwargs=parsing_kwargs,
                )
                for cmd in commands
            }
        except Exception as exc:
            error_msg = get_error_message("E1038", hostname=task.host.name, exception=exc)
            logger.error(error_msg)
            return Result(host=task.host, result=error_msg, failed=True, exception=exc)

        # pylint: disable=broad-exception-caught
        try:
            host_facts = perform_data_extraction(
                task.host,
                command_specifications[task.host.platform][section.name],
                preformatted_facts,
                jinja_env=jinja_env,
                logger=logger,
                skip_list=section.exclude,
            )
        except Exception as exc:
            error_msg = get_error_message("E1039", hostname=task.host.name, exception=exc)
            logger.error(error_msg)
            return Result(host=task.host, result=error_msg, failed=True, exception=exc)

        # ---- 3. Schema Validation  -----------------------------------------------
        try:
            validate_jsonschema(host_facts, section.schema)
        except ValidationError as exc:
            error_msg = get_error_message("E1040", hostname=task.host.name, exception=exc)
            logger.error(error_msg)
            return Result(host=task.host, result=error_msg, failed=True)

        logger.debug(
            f"Facts getter completed ({section.name})- commands collected, parsed and formatted successfully: {task.host.name} {host_facts}"
        )

        facts[section.name] = host_facts

    return Result(host=task.host, result=facts, failed=False, name="get_device_facts")
