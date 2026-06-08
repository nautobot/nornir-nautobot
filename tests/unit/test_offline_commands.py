"""Pytest of Getting Command Outputs through Git."""

import json
from unittest.mock import MagicMock, patch

import pytest

from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.plugins.tasks.dispatcher.default import (
    DispatcherMixin,
    NapalmDefault,
    NetmikoDefault,
    ScrapliDefault,
)
from nornir_nautobot.utils.helpers import command_to_filename


def _make_obj(custom_fields=None, config_context=None):
    """Build a fake Nautobot device object with cf and config-context sources."""
    obj = MagicMock()
    obj.cf = custom_fields or {}
    obj.get_config_context.return_value = config_context or {}
    return obj


def test_command_to_filename():
    assert command_to_filename("show version") == "show_version"
    assert command_to_filename("show | include version") == "show__include_version"
    assert command_to_filename("show / version") == "show_version"
    assert command_to_filename("show:version*?") == "show_version"
    assert command_to_filename("show version", replacement="-") == "show-version"
    assert command_to_filename("show | section version", replacement="-") == "show--section-version"


@pytest.mark.parametrize("driver", [DispatcherMixin, NetmikoDefault, NapalmDefault, ScrapliDefault])
def test_offline_commands_default_is_false(driver):
    assert driver._offline_commands(_make_obj()) is False


def test_offline_commands_custom_field_wins():
    obj = _make_obj(custom_fields={"offline_commands": True}, config_context={"offline_commands": False})
    assert DispatcherMixin._offline_commands(obj) is True


def test_offline_commands_config_context_used_when_cf_key_absent():
    obj = _make_obj(config_context={"offline_commands": True})
    assert DispatcherMixin._offline_commands(obj) is True


def test_offline_commands_non_bool_falls_through_to_default():
    obj = _make_obj(custom_fields={"offline_commands": "yes"})
    assert DispatcherMixin._offline_commands(obj) is False


def test_parse_offline_output_default_returns_text():
    assert DispatcherMixin._parse_offline_output("show version output") == "show version output"


def test_get_git_command_reads_file(tmp_path):
    command_file = tmp_path / "show_version.txt"
    command_file.write_text("Cisco IOS XE", encoding="utf-8")
    task = MagicMock()
    result = DispatcherMixin.get_git_command(task, MagicMock(), "show version", str(command_file))
    assert result.result == "Cisco IOS XE"


def test_get_git_command_missing_file_raises(tmp_path):
    task = MagicMock()
    with pytest.raises(FileNotFoundError):
        DispatcherMixin.get_git_command(task, MagicMock(), "show version", str(tmp_path / "missing.txt"))


def test_get_git_command_read_error_raises_ioerror(tmp_path):
    command_file = tmp_path / "show_version.txt"
    command_file.write_text("data", encoding="utf-8")
    task = MagicMock()
    with patch("builtins.open", side_effect=OSError("boom")):
        with pytest.raises(IOError):
            DispatcherMixin.get_git_command(task, MagicMock(), "show version", str(command_file))


def test_netmiko_get_command_offline_returns_text():
    obj = _make_obj(custom_fields={"offline_commands": True})
    task = MagicMock()
    task.run.return_value = [MagicMock(result="hostname router1")]
    result = NetmikoDefault.get_command(task, MagicMock(), obj, "show run", command_file_path="/repo/show_run.txt")
    assert result.result == {"output": {"show run": "hostname router1"}}
    # Offline path must route through get_git_command, never the live netmiko task.
    assert task.run.call_args.kwargs["task"] == NetmikoDefault.get_git_command


def test_netmiko_get_commands_offline_returns_text():
    obj = _make_obj(custom_fields={"offline_commands": True})
    task = MagicMock()
    task.run.side_effect = [
        [MagicMock(result="ver-output")],
        [MagicMock(result="run-output")],
    ]
    command_list = [("show version", "/repo/show_version.txt"), ("show run", "/repo/show_run.txt")]
    result = NetmikoDefault.get_commands(task, MagicMock(), obj, command_list)
    assert result.result == {"output": {"show version": "ver-output", "show run": "run-output"}}


def test_napalm_parse_offline_output_valid_json():
    parsed = NapalmDefault._parse_offline_output('{"running": "hostname r1"}')
    assert parsed == {"running": "hostname r1"}


def test_napalm_parse_offline_output_invalid_json_raises_e1041():
    with pytest.raises(NornirNautobotException) as exc_info:
        NapalmDefault._parse_offline_output("not json")
    assert "E1041" in str(exc_info.value)


def test_napalm_get_command_offline_parses_json():
    obj = _make_obj(custom_fields={"offline_commands": True})
    task = MagicMock()
    task.run.return_value = [MagicMock(result=json.dumps({"hostname": "r1"}))]
    result = NapalmDefault.get_command(task, MagicMock(), obj, "get_facts", command_file_path="/repo/get_facts.json")
    assert result.result == {"output": {"get_facts": {"hostname": "r1"}}}
    assert task.run.call_args.kwargs["task"] == NapalmDefault.get_git_command


def test_napalm_get_commands_offline_parses_each_file():
    obj = _make_obj(custom_fields={"offline_commands": True})
    task = MagicMock()
    task.run.side_effect = [
        [MagicMock(result=json.dumps({"hostname": "r1"}))],
        [MagicMock(result=json.dumps({"interfaces": {}}))],
    ]
    command_list = [("get_facts", "/repo/get_facts.json"), ("get_interfaces", "/repo/get_interfaces.json")]
    result = NapalmDefault.get_commands(task, MagicMock(), obj, command_list)
    assert result.result == {"output": {"get_facts": {"hostname": "r1"}, "get_interfaces": {"interfaces": {}}}}


def test_napalm_get_commands_offline_error_reports_get_commands_method():
    from nornir.core.exceptions import NornirSubTaskError

    obj = _make_obj(custom_fields={"offline_commands": True})
    task = MagicMock()
    task.run.side_effect = NornirSubTaskError(task=MagicMock(), result=MagicMock())
    with pytest.raises(NornirNautobotException) as exc_info:
        NapalmDefault.get_commands(task, MagicMock(), obj, [("get_facts", "/repo/get_facts.json")])
    assert "get_commands" in str(exc_info.value)


def test_scrapli_get_command_offline_returns_text():
    obj = _make_obj(custom_fields={"offline_commands": True})
    task = MagicMock()
    task.run.return_value = [MagicMock(result="hostname router1")]
    result = ScrapliDefault.get_command(task, MagicMock(), obj, "show run", command_file_path="/repo/show_run.txt")
    assert result.result == {"output": {"show run": "hostname router1"}}
    assert task.run.call_args.kwargs["task"] == ScrapliDefault.get_git_command


def test_scrapli_get_commands_offline_returns_text():
    obj = _make_obj(custom_fields={"offline_commands": True})
    task = MagicMock()
    task.run.side_effect = [
        [MagicMock(result="ver-output")],
        [MagicMock(result="run-output")],
    ]
    command_list = [("show version", "/repo/show_version.txt"), ("show run", "/repo/show_run.txt")]
    result = ScrapliDefault.get_commands(task, MagicMock(), obj, command_list)
    assert result.result == {"output": {"show version": "ver-output", "show run": "run-output"}}


# --- force_offline: caller-driven offline without the offline_commands SoT lookup (NAPPS-1235) ---


def test_netmiko_get_command_force_offline_reads_git_with_empty_obj():
    # Empty cf/config_context -> _offline_commands is False; force_offline alone must drive the offline path.
    obj = _make_obj()
    task = MagicMock()
    task.run.return_value = [MagicMock(result="hostname router1")]
    result = NetmikoDefault.get_command(
        task, MagicMock(), obj, "show run", command_file_path="/repo/show_run.txt", force_offline=True
    )
    assert result.result == {"output": {"show run": "hostname router1"}}
    assert task.run.call_args.kwargs["task"] == NetmikoDefault.get_git_command


def test_netmiko_get_command_force_offline_false_uses_live_path():
    obj = _make_obj()
    task = MagicMock()
    task.run.return_value = [MagicMock(result="hostname router1")]
    NetmikoDefault.get_command(task, MagicMock(), obj, "show run", force_offline=False)
    # Live path routes through netmiko_send_command, not the Git reader.
    assert task.run.call_args.kwargs["task"] != NetmikoDefault.get_git_command


def test_netmiko_get_command_force_offline_overrides_explicit_false_offline_commands():
    # Device explicitly opts out of offline, but the caller forces it.
    obj = _make_obj(custom_fields={"offline_commands": False})
    task = MagicMock()
    task.run.return_value = [MagicMock(result="hostname router1")]
    result = NetmikoDefault.get_command(
        task, MagicMock(), obj, "show run", command_file_path="/repo/show_run.txt", force_offline=True
    )
    assert result.result == {"output": {"show run": "hostname router1"}}
    assert task.run.call_args.kwargs["task"] == NetmikoDefault.get_git_command


def test_napalm_get_command_force_offline_parses_json_with_empty_obj():
    obj = _make_obj()
    task = MagicMock()
    task.run.return_value = [MagicMock(result=json.dumps({"hostname": "r1"}))]
    result = NapalmDefault.get_command(
        task, MagicMock(), obj, "get_facts", command_file_path="/repo/get_facts.json", force_offline=True
    )
    assert result.result == {"output": {"get_facts": {"hostname": "r1"}}}
    assert task.run.call_args.kwargs["task"] == NapalmDefault.get_git_command


def test_scrapli_get_command_force_offline_reads_git_with_empty_obj():
    obj = _make_obj()
    task = MagicMock()
    task.run.return_value = [MagicMock(result="hostname router1")]
    result = ScrapliDefault.get_command(
        task, MagicMock(), obj, "show run", command_file_path="/repo/show_run.txt", force_offline=True
    )
    assert result.result == {"output": {"show run": "hostname router1"}}
    assert task.run.call_args.kwargs["task"] == ScrapliDefault.get_git_command
