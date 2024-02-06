"""Used to setup fixtures to be used through tests."""

import pytest
import pynautobot
from nornir_nautobot.plugins.inventory.nautobot import NautobotInventory


@pytest.fixture()
def nornir_nautobot_class(monkeypatch):
    """Provide True to make tests pass.

    Returns:
        (bool): Returns True
    """
    monkeypatch.setattr(pynautobot.api, "version", "2.0")
    return NautobotInventory(nautobot_url="http://mock.example.com", nautobot_token="0123456789abcdef01234567890")
