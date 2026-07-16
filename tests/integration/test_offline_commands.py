"""End-to-end offline-command tests driving real Nornir task execution.

Unlike the unit tests in ``tests/unit/test_offline_commands.py`` (which mock
``task.run``), these run the dispatcher classmethods through a real Nornir
runner so the full offline chain executes: ``task.run`` -> ``get_git_command``
-> on-disk file read -> ``_parse_offline_output`` -> ``Result``. No device
connection is opened, so the suite needs no network access.
"""

import json

import pytest
from nornir.core.exceptions import NornirSubTaskError

from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.plugins.tasks.dispatcher.default import (
    NapalmDefault,
    NetmikoDefault,
    ScrapliDefault,
)

# (hostname, dispatcher) pairs whose stored output is raw command text.
RAW_TEXT_DEVICES = [
    ("ios-device", NetmikoDefault),
    ("eos-device", ScrapliDefault),
    ("iosxr-device", NetmikoDefault),
    ("nxos-device", NetmikoDefault),
    ("junos-device", NetmikoDefault),
]


@pytest.mark.parametrize("host, dispatcher", RAW_TEXT_DEVICES)
def test_get_command_force_offline_reads_raw_text(
    run_dispatcher, logger, device_factory, command_outputs_dir, host, dispatcher
):
    """force_offline reads the stored text file end-to-end for text drivers."""
    command_file = command_outputs_dir / host / "show_version.txt"
    expected = command_file.read_text(encoding="utf-8")

    result = run_dispatcher(
        host,
        dispatcher.get_command,
        logger=logger,
        obj=device_factory(),
        command="show version",
        command_file_path=str(command_file),
        force_offline=True,
    )

    assert not result.failed
    assert result[0].result == {"output": {"show version": expected}}


def test_napalm_get_command_force_offline_parses_json(run_dispatcher, logger, device_factory, command_outputs_dir):
    """force_offline deserializes a NAPALM getter file into structured data."""
    command_file = command_outputs_dir / "ios-device" / "get_facts.json"
    expected = json.loads(command_file.read_text(encoding="utf-8"))

    result = run_dispatcher(
        "ios-device",
        NapalmDefault.get_command,
        logger=logger,
        obj=device_factory(),
        command="get_facts",
        command_file_path=str(command_file),
        force_offline=True,
    )

    assert not result.failed
    assert result[0].result == {"output": {"get_facts": expected}}


def test_napalm_get_command_force_offline_malformed_json_raises_e1041(
    run_dispatcher, logger, device_factory, command_outputs_dir
):
    """A NAPALM offline file that is not valid JSON surfaces E1041."""
    command_file = command_outputs_dir / "ios-device" / "malformed.json"

    result = run_dispatcher(
        "ios-device",
        NapalmDefault.get_command,
        logger=logger,
        obj=device_factory(),
        command="get_facts",
        command_file_path=str(command_file),
        force_offline=True,
    )

    assert result.failed
    exception = result[0].exception
    assert isinstance(exception, NornirNautobotException)
    assert "E1041" in str(exception)


def test_get_command_force_offline_missing_file_does_not_fall_back(
    run_dispatcher, logger, device_factory, command_outputs_dir
):
    """A missing offline file fails (E1032 root) rather than querying a live device."""
    missing = command_outputs_dir / "ios-device" / "does_not_exist.txt"

    result = run_dispatcher(
        "ios-device",
        NetmikoDefault.get_command,
        logger=logger,
        obj=device_factory(),
        command="show version",
        command_file_path=str(missing),
        force_offline=True,
    )

    assert result.failed
    assert isinstance(result[0].exception, NornirNautobotException)
    # The dispatcher wraps the failure, but the root cause is the E1032 file-not-found
    # raised by get_git_command — proving there is no live fallback.
    root = next(r.exception for r in result if isinstance(r.exception, (FileNotFoundError, NornirSubTaskError)))
    assert isinstance(root, FileNotFoundError)
    assert "E1032" in str(root)


def test_netmiko_get_commands_offline_reads_each_file(run_dispatcher, logger, device_factory, command_outputs_dir):
    """get_commands honours the offline_commands gate and reads one file per command."""
    show_version = command_outputs_dir / "ios-device" / "show_version.txt"
    show_run = command_outputs_dir / "ios-device" / "show_run.txt"

    result = run_dispatcher(
        "ios-device",
        NetmikoDefault.get_commands,
        logger=logger,
        obj=device_factory(custom_fields={"offline_commands": True}),
        command_list=[
            ("show version", str(show_version)),
            ("show run", str(show_run)),
        ],
    )

    assert not result.failed
    assert result[0].result == {
        "output": {
            "show version": show_version.read_text(encoding="utf-8"),
            "show run": show_run.read_text(encoding="utf-8"),
        }
    }


def test_netmiko_get_config_offline_returns_stored_config(run_dispatcher, logger, device_factory, command_outputs_dir):
    """get_config reads the stored running config when offline_commands is enabled."""
    show_run = command_outputs_dir / "ios-device" / "show_run.txt"
    obj = device_factory(custom_fields={"offline_commands": True, "config_command": "show run"})

    result = run_dispatcher(
        "ios-device",
        NetmikoDefault.get_config,
        logger=logger,
        obj=obj,
        backup_file=None,
        remove_lines=[],
        substitute_lines=[],
        command_file_path=str(show_run),
    )

    assert not result.failed
    assert result[0].result == {"config": show_run.read_text(encoding="utf-8")}
