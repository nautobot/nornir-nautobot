"""Helper functions."""

import json

from nornir.core.task import Result
from ntc_templates.parse import parse_output as parse_output_fsm
from ttp import ttp as parse_output_ttp


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
