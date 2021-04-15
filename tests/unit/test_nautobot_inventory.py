"""Pytest of Nautobot Inventory."""
# Standard Library Imports
from os import path

# Third Party Imports
import pytest
from requests.sessions import Session
import pynautobot
from requests_mock import Mocker
from nornir import InitNornir
from nornir.core.task import Task

# Application Imports
from nornir_nautobot.plugins.inventory.nautobot import NautobotInventory

# GLOBALS
HERE = path.abspath(path.dirname(__file__))
API_CALLS = [
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

# Functions for helping tests
def load_api_calls(mock):
    """Loads API calls for mocker

    Args:
        mock (Request Mock): Requests Mock instance
    """
    for api_call in API_CALLS:
        with open(api_call["fixture_path"], "r") as _file:
            api_call["text"] = _file.read()

        mock.request(method=api_call["method"], url=api_call["url"], text=api_call["text"], complete_qs=True)


#
# Tests
#
def test_nornir_nautobot_initialization():
    # Set a var
    no_exception_found = True
    try:
        NautobotInventory(nautobot_url="http://localhost:8000", nautobot_token="0123456789abcdef01234567890")
    except:  # pylint: disable=bare-except
        no_exception_found = False

    assert no_exception_found


def test_nornir_nautobot_missing_url():
    with pytest.raises(ValueError) as err:
        NautobotInventory(nautobot_url=None, nautobot_token="0123456789abcdef01234567890")

    assert str(err.value) == "Missing URL or Token from parameters or environment."


def test_nornir_nautobot_missing_token():
    with pytest.raises(ValueError) as err:
        NautobotInventory(nautobot_url="http://localhost:8000", nautobot_token=None)

    assert str(err.value) == "Missing URL or Token from parameters or environment."


def test_api_session(nornir_nautobot_class):
    expected_headers = {
        "User-Agent": "python-requests/2.25.1",
        "Accept-Encoding": "gzip, deflate",
        "Accept": "*/*",
        "Connection": "keep-alive",
    }
    assert isinstance(nornir_nautobot_class.api_session, Session)
    assert expected_headers == nornir_nautobot_class.api_session.headers


def test_pynautobot_obj(nornir_nautobot_class):
    assert isinstance(nornir_nautobot_class.pynautobot_obj, pynautobot.api)


def test_devices(nornir_nautobot_class):
    # Import mock requests
    with Mocker() as mock:
        load_api_calls(mock)
        pynautobot_obj = pynautobot.api(url="http://mock.example.com", token="0123456789abcdef01234567890")
        expected_devices = []
        for device in ["den-dist01", "den-dist02", "den-wan01"]:
            expected_devices.append(pynautobot_obj.dcim.devices.get(name=device))

        assert nornir_nautobot_class.devices == expected_devices


def test_filter_devices():
    with Mocker() as mock:
        load_api_calls(mock)
        test_class = NautobotInventory(
            nautobot_url="http://mock.example.com",
            nautobot_token="0123456789abcdef01234567890",
            filter_parameters={"site": "msp"},
        )
        pynautobot_obj = pynautobot.api(url="http://mock.example.com", token="0123456789abcdef01234567890")
        expected_devices = []
        for device in ["msp-rtr01", "msp-rtr02"]:
            expected_devices.append(pynautobot_obj.dcim.devices.get(name=device))

        assert test_class.devices == expected_devices


def test_device_required_properties():
    def mock_nornir_task(task: Task):
        """Example to show work inside of a task.

        Args:
            task (Task): Nornir Task
        """
        return task.host.platform

    with Mocker() as mock:
        load_api_calls(mock)
        test_nornir = InitNornir(
            inventory={
                "plugin": "NautobotInventory",
                "options": {
                    "nautobot_url": "http://mock.example.com",
                    "nautobot_token": "0123456789abcdef01234567890",
                    "filter_parameters": {"site": "msp"},
                },
            },
        )

    # Run through Nornir tasks
    nornir_task_result = test_nornir.run(task=mock_nornir_task)

    # Verify expected result
    for task_result in nornir_task_result:
        assert nornir_task_result[task_result].result == "ios"
