"""A set of helper utilities."""

import errno
import importlib
import json
import logging
import os
import re
import traceback
import unicodedata
from typing import Any

from nornir.core.task import Result
from ntc_templates.parse import parse_output as parse_output_fsm
from ttp import ttp as parse_output_ttp

from nornir_nautobot.constants import ERROR_CODES

LOGGER = logging.getLogger(__name__)


def make_folder(folder):
    """Helper method to sanely create folders."""
    if not os.path.exists(folder):
        # Still try and except, since their may be race conditions.
        try:
            os.makedirs(folder)
        except OSError as error:
            if error.errno != errno.EEXIST:
                raise


def snake_to_title_case(snake_string):
    """Convert snake_case into TitleCase."""
    return "".join(word.capitalize() for word in snake_string.lower().split("_"))


def import_string(dotted_path):
    """Import the python object by dotted_path string ."""
    module_name, class_name = dotted_path.rsplit(".", 1)
    try:
        return getattr(importlib.import_module(module_name), class_name)
    except (ModuleNotFoundError, AttributeError):
        return None


def get_stack_trace(exc: Exception) -> str:
    """Converts the provided exception's stack trace into a string."""
    stack_trace_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    return "".join(stack_trace_lines)


def is_truthy(arg):
    """Convert "truthy" strings into Booleans.

    Args:
        arg (str): Truthy string (True values are y, yes, t, true, on and 1; false values are n, no,
        f, false, off and 0. Raises ValueError if val is anything else.

    Examples:
        >>> is_truthy('yes')
        True
    """
    if isinstance(arg, bool):
        return arg

    val = str(arg).lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    if val in ("n", "no", "f", "false", "off", "0"):
        return False
    return True


def get_error_message(error_code: str, **kwargs: Any) -> str:
    """Get the error message for a given error code.

    Args:
        error_code (str): The error code.
        **kwargs: Any additional context data to be interpolated in the error message.

    Returns:
        str: The constructed error message.
    """
    try:
        error_message = ERROR_CODES.get(error_code, ERROR_CODES["E1XXX"]).error_message.format(**kwargs)
    except KeyError as missing_kwarg:
        error_message = f"Error Code was found, but failed to format, message expected kwarg `{missing_kwarg}`."
    except Exception:  # pylint: disable=broad-except
        error_message = "Error Code was found, but failed to format message, unknown cause."
    return f"{error_code}: {error_message}"


def command_to_filename(command, replacement="_"):
    """
    Convert a command string into a filesystem-safe filename.

    This function sanitizes a command string so it can safely be used as a filename by:
    1. Normalizing Unicode characters to their ASCII equivalents.
    2. Replacing the pipe symbol '|' (with or without surrounding spaces) with two replacement characters.
    3. Replacing characters that are illegal in most filesystems (e.g., / : * ? " < >) with the replacement character.
    4. Replacing all spaces with the replacement character.

    Args:
        command (str): The input command string to sanitize.
        replacement (str): The character to use as a substitute for illegal or special characters. Default is underscore ('_').

    Returns:
        str: A sanitized, ASCII-only, filesystem-safe version of the command string suitable for use as a filename.
    """
    # 1. Normalize Unicode characters (e.g., accented characters to ASCII equivalents)
    #    and then ignore non-ASCII. This handles many international characters.
    command_file_name = unicodedata.normalize("NFKD", command).encode("ascii", "ignore").decode("ascii")

    # 2. Replace the '|' with the replacement character
    command_file_name = re.sub(r"\s*\|\s*", 2 * replacement, command_file_name)

    # 3. Replace characters illegal in most filesystems with the replacement character
    #    Common illegal characters: / \ : * ? " < > |
    #    Also replace leading/trailing whitespace, and control characters.
    #    This regex targets common illegal filename characters and also handles multiple
    #    replacement characters in a row (e.g., 'foo///bar' becomes 'foo_bar').
    command_file_name = re.sub(r"\s*[\/\\:*?\"<>]\s*", replacement, command_file_name)

    # 4. Replace spaces with the replacement character
    command_file_name = re.sub(r"\s+", replacement, command_file_name).strip(replacement)

    return command_file_name


def parse_textfsm(
    platform,
    command,
    data,
    templates_dir,
    *,
    logger=None,
):
    """
    Parse command output using TextFSM.

    Args:
        platform: Network OS / driver name.
        command: Command string.
        data: Raw command output.
        templates_dir: Directory containing TextFSM templates.
        logger: Optional logger for debug output.

    Returns:
        Parsed output as a list of dicts.
    """
    parsed_output = parse_output_fsm(
        platform=platform,
        template_dir=templates_dir,
        command=command,
        data=data,
        try_fallback=bool(templates_dir),
    )

    if logger:
        logger.debug(
            "Parsed TextFSM output of '%s' command:\n\n%s",
            command,
            parsed_output,
        )

    return parsed_output


def parse_ttp(
    platform,
    command,
    data,
    templates_files,
    *,
    logger=None,
):
    """
    Parse command output using TTP.

    Args:
        platform: Network OS / driver name.
        command: Command string.
        data: Raw command output.
        templates_files: Mapping of template filenames to template content.
        logger: Optional logger for debug output.

    Returns:
        Parsed output as Python data.
    """
    template_name = f"{platform}_{command.replace(' ', '_')}.ttp"
    parser = parse_output_ttp(data=data, template=templates_files[template_name])
    parser.parse()

    parsed_output = json.loads(parser.result(format="json")[0])

    if logger:
        logger.debug(
            "Parsed TTP output of '%s' command:\n\n%s",
            command,
            parsed_output,
        )

    return parsed_output


PARSERS = {
    "textfsm": parse_textfsm,
    "ttp": parse_ttp,
}


def _deduplicate_command_list(data, elem_type="command"):
    """Deduplicates a list of dictionaries based on 'command' and 'parser' keys.

    Args:
        data: A list of dictionaries.
        elem_type: The type of element to deduplicate (oid or command).

    Returns:
        A new list containing only unique elements based on 'command' and 'parser'.
    """
    seen = set()
    unique_list = []
    for item in data:
        # Create a tuple containing only 'command' and 'parser' for comparison
        key = (item[elem_type], item["parser"])
        if key not in seen:
            seen.add(key)
            unique_list.append(item)
    return unique_list


def _get_elements_to_run(yaml_parsed_info, skip_list=None, elements="commands"):
    """Return a deduplicated list of commands to run based on YAML info and sync flags."""
    all_commands = []

    for key, value in yaml_parsed_info.items():
        # Handle pre_processor section separately
        if key == "pre_processor":
            for pre_processor_name, pre_processor_value in value.items():
                # Skip if this key shouldn't be synced
                if skip_list and (pre_processor_name in skip_list):
                    continue
                commands = pre_processor_value.get(elements, [])
                if isinstance(commands, dict):
                    all_commands.append(commands)
                elif isinstance(commands, list):
                    all_commands.extend(commands)
            continue  # move to next key

        # Skip if this key shouldn't be synced
        if skip_list and (key in skip_list):
            continue

        commands = value.get(elements, [])
        if isinstance(commands, dict):
            all_commands.append(commands)
        elif isinstance(commands, list):
            all_commands.extend(commands)

    return _deduplicate_command_list(all_commands, elements[:-1])  # Strip `s` - could be more elegant here.


def _validate_platform_parsing_info(task, yaml_data, job):
    """Check platform and YAML definition validity."""
    platform = task.host.platform

    if not platform:
        return Result(host=task.host, result=f"{task.host.name} has no platform set.", failed=True)

    if not yaml_data.get(platform, {}).get(job):
        return Result(
            host=task.host,
            result=f"{task.host.name} missing definitions in command_mapper YAML.",
            failed=True,
        )

    return Result(host=task.host, result=f"{task.host.name} assigned platform {platform} section.", failed=False)


def _parse_command_result(network_driver, command, raw_output, parser_type, logger, parsing_kwargs):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """Parse and store results based on parser type."""
    logger.debug("Result of '%s' command:\n\n%s", command, raw_output)

    if parser_type in list(PARSERS.keys()):  # pylint: disable=consider-iterating-dictionary
        parsed = _parse_command_output(network_driver, command, raw_output, parser_type, logger, parsing_kwargs)
    else:
        parsed = _handle_raw_or_none(raw_output, parser_type)

    return parsed


def _parse_command_output(network_driver, command, raw_output, parser_type, logger, parsing_kwargs):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    # pylint: disable=broad-exception-caught
    try:
        parser = PARSERS.get(parser_type)
        if not parser:
            return []

        return parser(
            platform=network_driver,
            command=command,
            data=raw_output,
            logger=logger,
            **parsing_kwargs[parser_type],
        )
    except Exception as e:
        logger.warning("Parsing failed for %s: %s", command, e)
        return []


def _handle_raw_or_none(raw_output, parser_type):
    """Handle raw and none parsers."""
    if parser_type == "raw":
        return {"raw": raw_output}
    if parser_type == "none":
        # pylint: disable=broad-exception-caught
        try:
            return json.loads(raw_output)
        except Exception:
            return []
    return []
