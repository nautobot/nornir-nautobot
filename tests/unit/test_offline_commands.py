"""Pytest of Getting Command Outputs through Git."""

from nornir_nautobot.utils.helpers import command_to_filename


def test_command_to_filename():
    assert command_to_filename("show version") == "show_version"
    assert command_to_filename("show | include version") == "show__include_version"
    assert command_to_filename("show / version") == "show_version"
    assert command_to_filename("show:version*?") == "show_version"
    assert command_to_filename("show version", replacement="-") == "show-version"
    assert command_to_filename("show | section version", replacement="-") == "show--section-version"
