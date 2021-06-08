"""Used to setup fixtures to be used through tests."""
import pytest
from nornir_nautobot.plugins.inventory.nautobot import NautobotInventory
from nornir import InitNornir
from os import path

# GLOBALS
HERE = path.abspath(path.dirname(__file__))
MOCK_API_CALLS = [
    {
        "fixture_path": f"{HERE}/mocks/01_get_devices.json",
        "url": "http://mock.example.com/api/dcim/devices/",
        "method": "get",
    },
    {
        "fixture_path": f"{HERE}/mocks/02_get_device1.json",
        "url": "http://mock.example.com/api/dcim/devices/?name=den-dist01",
        "method": "get",
    },
    {
        "fixture_path": f"{HERE}/mocks/03_get_device2.json",
        "url": "http://mock.example.com/api/dcim/devices/?name=den-dist02",
        "method": "get",
    },
    {
        "fixture_path": f"{HERE}/mocks/04_get_device3.json",
        "url": "http://mock.example.com/api/dcim/devices/?name=den-wan01",
        "method": "get",
    },
    {
        "fixture_path": f"{HERE}/mocks/05_get_sites_filtered.json",
        "url": "http://mock.example.com/api/dcim/devices/?site=msp",
        "method": "get",
    },
    {
        "fixture_path": f"{HERE}/mocks/06_get_device_msp-rtr01.json",
        "url": "http://mock.example.com/api/dcim/devices/?name=msp-rtr01",
        "method": "get",
    },
    {
        "fixture_path": f"{HERE}/mocks/07_get_device_msp-rtr02.json",
        "url": "http://mock.example.com/api/dcim/devices/?name=msp-rtr02",
        "method": "get",
    },
]


@pytest.fixture()
def mock_api_calls(requests_mock):
    """Loads API calls for mocker

    Args:
        mock (Request Mock): Requests Mock instance
    """
    for api_call in MOCK_API_CALLS:
        with open(api_call["fixture_path"], "r") as _file:
            api_call["text"] = _file.read()
        requests_mock.request(method=api_call["method"], url=api_call["url"], text=api_call["text"], complete_qs=True)


@pytest.fixture()
def nornir_nautobot_class():
    """Provide True to make tests pass.

    Returns:
        (bool): Returns True
    """
    return NautobotInventory(nautobot_url="http://mock.example.com", nautobot_token="0123456789abcdef01234567890")


@pytest.fixture()
def nornir_no_pynb_dict(mock_api_calls):
    """
    Nautobot Inventory without pynautobot dict set

    Returns:
        (NautobotInventory): inventory
    """
    return InitNornir(
        inventory={
            "plugin": "NautobotInventory",
            "options": {
                "nautobot_url": "http://mock.example.com",
                "nautobot_token": "0123456789abcdef01234567890",
                "pynautobot_dict": False,
            },
        },
        logging={"enabled": False},
    )


@pytest.fixture()
def nornir_with_pynb_dict(mock_api_calls):
    """
    Nautobot Inventory with pynautobot dict toggle to True

    Returns:
        (NautobotInventory): inventory
    """
    return InitNornir(
        inventory={
            "plugin": "NautobotInventory",
            "options": {
                "nautobot_url": "http://mock.example.com",
                "nautobot_token": "0123456789abcdef01234567890",
            },
        },
        logging={"enabled": False},
    )