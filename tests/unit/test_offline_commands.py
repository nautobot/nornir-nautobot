"""Pytest of Getting Command Outputs through Git."""

# import pytest
# import tempfile
# from pathlib import Path
# from unittest.mock import MagicMock
# from nornir_nautobot.utils.helpers import command_to_filename, get_file_contents_from_git

from nornir_nautobot.utils.helpers import command_to_filename


def test_command_to_filename():
    assert command_to_filename("show version") == "show_version"
    assert command_to_filename("show | include version") == "show__include_version"
    assert command_to_filename("show / version") == "show_version"
    assert command_to_filename("show:version*?") == "show_version"
    assert command_to_filename("show version", replacement="-") == "show-version"
    assert command_to_filename("show | section version", replacement="-") == "show--section-version"
