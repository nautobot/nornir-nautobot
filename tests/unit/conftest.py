"""Used to setup fixtures to be used through tests."""

import json
from pathlib import Path
from typing import Any

import pynautobot
import pytest

from nornir_nautobot.plugins.inventory.nautobot import NautobotInventory


@pytest.fixture
def nornir_nautobot_class(monkeypatch):
    """Provide True to make tests pass.

    Returns:
        (bool): Returns True
    """
    monkeypatch.setattr(pynautobot.api, "version", "2.0")
    return NautobotInventory(nautobot_url="http://mock.example.com", nautobot_token="0123456789abcdef01234567890")


def get_json_fixture(folder: str, file_name: str) -> dict[str, Any]:
    """Fixture to return a mock config context for tests.

    Args:
        folder (str): The folder where the config context file is located.
        file_name (str): The name of the config context file.

    Returns:
        dict[str, Any]: The mock config context.
    """
    context_file: Path = Path(__file__).parent.joinpath(
        "fixtures",
        folder,
        file_name,
    )
    with Path(context_file).open(mode="r", encoding="utf-8") as file:
        context: dict[str, Any] = json.load(fp=file)
    return context
