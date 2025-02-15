"""Pytest of Nautobot Inventory."""

# Standard Library Imports
from os import path

import pynautobot

# Third Party Imports
import pytest
import requests
from requests.sessions import Session
from requests_mock import Mocker
from nornir import InitNornir
from nornir.core.task import Task

# Application Imports
from nornir_nautobot.plugins.inventory.nautobot import NautobotInventory

# GLOBALS
HERE = path.abspath(path.dirname(__file__))
API_CALLS = [
    {
        "fixture_path": f"{HERE}/mocks/00_api_root.json",
        "url": "http://mock.example.com/api/",
        "method": "get",
    },
    {
        "fixture_path": f"{HERE}/mocks/00_api_root.json",
        "url": "https://mock.example.com/api/",
        "method": "get",
    },
    {
        "fixture_path": f"{HERE}/mocks/01_get_devices.json",
        "url": "http://mock.example.com/api/dcim/devices/?depth=1",
        "method": "get",
    },
    {
        "fixture_path": f"{HERE}/mocks/01_get_devices.json",
        "url": "https://mock.example.com/api/dcim/devices/?depth=1",
        "method": "get",
    },
    {
        "fixture_path": f"{HERE}/mocks/01_get_devices.json",
        "url": "https://mock.example.com/api/dcim/devices/?depth=1&limit=0",
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
        "fixture_path": f"{HERE}/mocks/05_get_locations_filtered.json",
        "url": "http://mock.example.com/api/dcim/devices/?depth=1&location=msp",
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
    """Loads API calls for mocker.

    Args:
        mock (Request Mock): Requests Mock instance
    """
    for api_call in API_CALLS:
        with open(api_call["fixture_path"], "r", encoding="utf-8") as _file:
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


def test_nornir_nautobot_initialization_ssl_verify_default():
    with Mocker() as mock:
        load_api_calls(mock)
        nornir_nautobot_class = NautobotInventory(
            nautobot_url="https://mock.example.com", nautobot_token="0123456789abcdef01234567890"
        )
        assert nornir_nautobot_class.pynautobot_obj.http_session.verify is True
        assert nornir_nautobot_class.api_session.verify is True
        assert nornir_nautobot_class.ssl_verify is True


def test_nornir_nautobot_initialization_ssl_verify_false():
    with Mocker() as mock:
        load_api_calls(mock)
        nornir_nautobot_class = NautobotInventory(
            nautobot_url="https://mock.example.com", nautobot_token="0123456789abcdef01234567890", ssl_verify=False
        )
        assert nornir_nautobot_class.pynautobot_obj.http_session.verify is False
        assert nornir_nautobot_class.api_session.verify is False
        assert nornir_nautobot_class.ssl_verify is False


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
        "User-Agent": f"python-requests/{requests.__version__}",
        "Accept-Encoding": "gzip, deflate, zstd",
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
            filter_parameters={"location": "msp"},
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
                    "filter_parameters": {"location": "msp"},
                },
            },
        )

    # Run through Nornir tasks
    nornir_task_result = test_nornir.run(task=mock_nornir_task)

    # Verify expected result
    for task_result in nornir_task_result:
        assert nornir_task_result[task_result].result == "ios"


def test_nornir_nautobot_device_count():
    # Import mock requests
    with Mocker() as mock:
        load_api_calls(mock)
        test_nornir = InitNornir(
            inventory={
                "plugin": "NautobotInventory",
                "options": {
                    "nautobot_url": "http://mock.example.com",
                    "nautobot_token": "0123456789abcdef01234567890",
                },
            },
        )

    # Verify that the length of the inventory is 3 devices
    assert len(test_nornir.inventory.hosts) == 3


def test_nornir_nautobot_with_defaults():
    """
    Tests that nornir defaults are getting applied to NautobotInventory hosts
    """
    with Mocker() as mock:
        load_api_calls(mock)
        nr_obj = InitNornir(
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
        nr_obj.inventory.defaults.username = "username"
        nr_obj.inventory.defaults.password = "password"

        assert nr_obj.inventory.hosts["den-dist01"].username == nr_obj.inventory.defaults.username
        assert nr_obj.inventory.hosts["den-dist02"].password == nr_obj.inventory.defaults.password


@pytest.mark.parametrize(
    "device, expected_platform", [("den-dist01", None), ("den-wan01", "ios"), ("den-dist02", "ios")]
)
def test_nornir_nautobot_device_platform(device, expected_platform):
    # Import mock requests
    with Mocker() as mock:
        load_api_calls(mock)
        test_nornir = InitNornir(
            inventory={
                "plugin": "NautobotInventory",
                "options": {
                    "nautobot_url": "http://mock.example.com",
                    "nautobot_token": "0123456789abcdef01234567890",
                },
            },
        )

    assert test_nornir.inventory.hosts[device].platform == expected_platform


@pytest.mark.parametrize(
    "device, expected_hostname", [("den-dist01", "10.17.1.2"), ("den-wan01", "10.16.0.2"), ("den-dist02", "10.17.1.6")]
)
def test_nornir_nautobot_device_hostname(device, expected_hostname):
    # Import mock requests
    with Mocker() as mock:
        load_api_calls(mock)
        test_nornir = InitNornir(
            inventory={
                "plugin": "NautobotInventory",
                "options": {
                    "nautobot_url": "http://mock.example.com",
                    "nautobot_token": "0123456789abcdef01234567890",
                },
            },
        )

    assert test_nornir.inventory.hosts[device].hostname == expected_hostname


# Setup of groups for a future PR
@pytest.mark.parametrize("device, expected_groups", [("den-dist01", []), ("den-wan01", []), ("den-dist02", [])])
def test_nornir_nautobot_device_groups(device, expected_groups):
    # Import mock requests
    with Mocker() as mock:
        load_api_calls(mock)
        test_nornir = InitNornir(
            inventory={
                "plugin": "NautobotInventory",
                "options": {
                    "nautobot_url": "http://mock.example.com",
                    "nautobot_token": "0123456789abcdef01234567890",
                },
            },
        )

    assert test_nornir.inventory.hosts[device].groups == expected_groups


@pytest.mark.parametrize("device", ["den-dist01", "den-wan01", "den-dist02"])
def test_pynautobot_as_dict(device):
    """
    Test the pynautobot flag sets the presence of a 'pynautobot_dictionary' data attribute
    """
    # Import mock requests
    with Mocker() as mock:
        load_api_calls(mock)
        nornir_with_pynb_dict = InitNornir(
            inventory={
                "plugin": "NautobotInventory",
                "options": {
                    "nautobot_url": "http://mock.example.com",
                    "nautobot_token": "0123456789abcdef01234567890",
                },
            },
            logging={"enabled": False},
        )
        assert "pynautobot_dictionary" in list(nornir_with_pynb_dict.inventory.hosts[device].keys())


@pytest.mark.parametrize("device", ["den-dist01", "den-wan01", "den-dist02"])
def test_no_pynautobot_as_dict(device):
    """
    Test the pynautobot flag unsets the presence of a 'pynautobot_dictionary' data attribute
    """
    # Import mock requests
    with Mocker() as mock:
        load_api_calls(mock)
        nornir_no_pynb_dict = InitNornir(
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
        assert "pynautobot_dictionary" not in list(nornir_no_pynb_dict.inventory.hosts[device].keys())
