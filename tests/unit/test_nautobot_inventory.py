"""Pytest of Nautobot Inventory."""
# Standard Library Imports
from os import path
from itertools import chain

# Third Party Imports
import pytest
from requests.sessions import Session
import pynautobot

# Application Imports
from nornir_nautobot.plugins.inventory.nautobot import NautobotInventory

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


def test_devices(mock_api_calls, nornir_nautobot_class):
    pynautobot_obj = pynautobot.api(url="http://mock.example.com", token="0123456789abcdef01234567890")
    expected_devices = []
    for device in ["den-dist01", "den-dist02", "den-wan01"]:
        expected_devices.append(pynautobot_obj.dcim.devices.get(name=device))

    assert nornir_nautobot_class.devices == expected_devices


def test_filter_devices(mock_api_calls):
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


def test_pynautobot_as_dict(nornir_no_pynb_dict, nornir_with_pynb_dict):
    """
    Test the pynautobot flag sets the presence of a 'pynautobot_dictionary' data attribute
    """
    keys_with_dict = [
        nornir_with_pynb_dict.inventory.hosts[device].keys() for device in ["den-dist01", "den-dist02", "den-wan01"]
    ]
    keys_no_dict = [
        nornir_no_pynb_dict.inventory.hosts[device].keys() for device in ["den-dist01", "den-dist02", "den-wan01"]
    ]
    attrs_with_dict = set(chain(*keys_with_dict))
    attrs_no_dict = set(chain(*keys_no_dict))
    attrs_diff = attrs_with_dict - attrs_no_dict
    assert attrs_diff == set(["pynautobot_dictionary"])