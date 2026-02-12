"""Test for formatter in get_device_facts nornir play."""

import json
import os
import unittest
from unittest.mock import MagicMock

import yaml
from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment
from nornir.core.inventory import ConnectionOptions, Host

from nornir_nautobot.utils.formatter import (
    extract_and_post_process,
    normalize_processed_data,
)

MOCK_DIR = os.path.join("tests", "unit", "get_device_facts_mocks")
SYNC_DEVICES_ONLY = ["cisco_wlc", "hp_comware", "paloalto_panos", "f5_tmsh", "aruba_aoscx"]


def find_files_by_prefix(directory, prefix):
    """Finds all files within a directory whose names start with the given prefix.

    Args:
        directory: The directory path to search.
        prefix: The prefix string to match in filenames.

    Returns:
        A list of filenames that start with the prefix.
    """
    matching_files = []
    for filename in os.listdir(directory):
        if filename.startswith(prefix):
            matching_files.append(filename)
    return matching_files


class TestFormatterNormalizeProccessedData(unittest.TestCase):
    """Tests to ensure normalize_processed_data is working."""

    def test_normalize_processed_data_str_stringified_integer(self):
        self.assertEqual(normalize_processed_data("7201", "str"), "7201")

    def test_normalize_processed_data_str__list_index_string(self):
        self.assertEqual(normalize_processed_data(["IOS-SW-1"], "str"), "IOS-SW-1")

    def test_normalize_processed_data_str__string(self):
        self.assertEqual(normalize_processed_data("Vlan10", "str"), "Vlan10")

    def test_normalize_processed_data_none_stringified_integer(self):
        self.assertEqual(normalize_processed_data("7201", None), "7201")

    def test_normalize_processed_data_none_list_index_string(self):
        self.assertEqual(normalize_processed_data(["IOS-SW-1"], None), "IOS-SW-1")

    def test_normalize_processed_data_none_string(self):
        self.assertEqual(normalize_processed_data("Vlan10", None), "Vlan10")

    def test_normalize_processed_data_none_int(self):
        self.assertEqual(normalize_processed_data(10, None), 10)

    def test_normalize_processed_data_empty_none(self):
        self.assertEqual(normalize_processed_data([], None), [])

    def test_normalize_processed_data_empty_str(self):
        self.assertEqual(normalize_processed_data([], "str"), "")

    def test_normalize_processed_data_empty_dict(self):
        self.assertEqual(normalize_processed_data([], "dict"), {})

    def test_normalize_processed_data_empty_int(self):
        self.assertEqual(normalize_processed_data([], "int"), [])

    def test_normalize_processed_data_str_int(self):
        self.assertEqual(normalize_processed_data(10, "str"), "10")

    def test_normalize_processed_data_int_str(self):
        self.assertEqual(normalize_processed_data("10", "int"), 10)

    def test_normalize_processed_data_int_int(self):
        self.assertEqual(normalize_processed_data(10, "int"), 10)

    def test_normalize_processed_data_int_list_index_int(self):
        self.assertEqual(normalize_processed_data([881], "int"), 881)


class TestFormatterExtractAndProcess(unittest.TestCase):
    """Tests Basic Operations of formatter."""

    def setUp(self):
        with open(f"{MOCK_DIR}/command_mappers/mock_cisco_ios.yml", "r", encoding="utf-8") as parsing_info:
            self.platform_parsing_info = yaml.safe_load(parsing_info)
        with open(f"{MOCK_DIR}/cisco_ios/command_getter_result_1.json", "r", encoding="utf-8") as command_info:
            self.command_outputs = json.loads(command_info.read())
        self.host = Host(
            name="198.51.100.1",
            hostname="198.51.100.1",
            port=22,
            username="username",
            password="password",  # nosec
            platform="cisco_ios",
            connection_options={
                "netmiko": ConnectionOptions(
                    hostname="198.51.100.1",
                    port=22,
                    username="username",
                    password="password",  # nosec
                    platform="platform",
                )
            },
        )
        self.logger = MagicMock()
        self.skip_list = [
            "cables",
            "interfaces__tagged_vlans",
            "interfaces__untagged_vlan",
            "interfaces__vrf",
            "software_version",
            "vlan_map",
        ]
        jinja_env_params = {
            "undefined": StrictUndefined,
            "trim_blocks": True,
            "lstrip_blocks": False,
        }
        self.jinja_env = SandboxedEnvironment(**jinja_env_params)

    def test_perform_data_extraction_simple_host_values(self):
        self.assertEqual("198.51.100.1", self.host.name)

    def test_extract_and_post_process_empty_command_result_str(self):
        parsed_command_output = ""
        actual_result = extract_and_post_process(
            parsed_command_output,
            self.platform_parsing_info["sync_devices"]["serial"],
            self.jinja_env,
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            self.logger,
        )
        expected_parsed_result = ("", [])
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_empty_command_result_list(self):
        parsed_command_output = []
        actual_result = extract_and_post_process(
            parsed_command_output,
            self.platform_parsing_info["sync_devices"]["serial"],
            self.jinja_env,
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            self.logger,
        )
        expected_parsed_result = ([], [])
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_empty_command_result_dict(self):
        parsed_command_output = {}
        actual_result = extract_and_post_process(
            parsed_command_output,
            self.platform_parsing_info["sync_devices"]["serial"],
            self.jinja_env,
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            self.logger,
        )
        expected_parsed_result = ({}, [])
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_empty_command_result_str_with_iterable(self):
        parsed_command_output = ""
        actual_result = extract_and_post_process(
            parsed_command_output,
            self.platform_parsing_info["sync_devices"]["serial"],
            self.jinja_env,
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            "str",
            self.logger,
        )
        expected_parsed_result = ("", "")
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_empty_command_result_list_with_iterable(self):
        parsed_command_output = []
        actual_result = extract_and_post_process(
            parsed_command_output,
            self.platform_parsing_info["sync_devices"]["serial"],
            self.jinja_env,
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            "dict",
            self.logger,
        )
        expected_parsed_result = ([], {})
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_empty_command_result_dict_with_iterable(self):
        parsed_command_output = {}
        actual_result = extract_and_post_process(
            parsed_command_output,
            self.platform_parsing_info["sync_devices"]["serial"],
            self.jinja_env,
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            "dict",
            self.logger,
        )
        expected_parsed_result = ({}, {})
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_dict_with_iterable(self):
        parsed_command_output = self.command_outputs["show version"]
        actual_result = extract_and_post_process(
            parsed_command_output,
            self.platform_parsing_info["sync_devices"]["serial"]["commands"][0],
            self.jinja_env,
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            self.logger,
        )
        expected_parsed_result = (["FOC2341Y2CQ"], "FOC2341Y2CQ")
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_json_string(self):
        parsed_command_output = '{"foo": "bar"}'
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "foo",
            },
            self.jinja_env,
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            self.logger,
        )
        expected_parsed_result = ("bar", "bar")
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_python_dict(self):
        parsed_command_output = {"foo": "bar"}
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "foo",
            },
            self.jinja_env,
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            self.logger,
        )
        expected_parsed_result = ("bar", "bar")
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_non_json_string(self):
        parsed_command_output = "baz"
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "foo",
            },
            self.jinja_env,
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            self.logger,
        )
        expected_parsed_result = ([], [])
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_non_json_string_with_iterable(self):
        parsed_command_output = "bar"
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "foo",
            },
            self.jinja_env,
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            "dict",
            self.logger,
        )
        expected_parsed_result = ([], {})
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_list_to_dict(self):
        parsed_command_output = [{"foo": {"bar": "moo"}}]
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "[*].foo",
            },
            self.jinja_env,
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            "dict",
            self.logger,
        )
        expected_parsed_result = ([{"bar": "moo"}], {"bar": "moo"})
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_list_to_string(self):
        parsed_command_output = ["foo"]
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "[*]",
            },
            self.jinja_env,
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            "str",
            self.logger,
        )
        expected_parsed_result = (["foo"], "foo")
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_default_iterable(self):
        parsed_command_output = [{"foo": {"bar": "moo"}}]
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "[*].foo",
            },
            self.jinja_env,
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            None,
            self.logger,
        )
        expected_parsed_result = ([{"bar": "moo"}], [{"bar": "moo"}])
        self.assertEqual(expected_parsed_result, actual_result)

    @unittest.skip("Temporarily disabled – Jinja2 filters loading pending")
    def test_extract_and_post_process_result_pre_processor(self):
        parsed_command_output = [
            {
                "access_vlan": "10",
                "admin_mode": "trunk",
                "interface": "Gi1/8",
                "mode": "down (suspended member of bundle Po8)",
                "native_vlan": "10",
                "switchport": "Enabled",
                "switchport_monitor": "",
                "switchport_negotiation": "Off",
                "trunking_vlans": ["10"],
                "voice_vlan": "none",
            }
        ]
        vlan_map_post_processed = {"1": "default", "10": "10.39.110.0/25.LAN"}
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show interfaces switchport",
                "parser": "textfsm",
                "jpath": "[?interface=='{{ current_key | abbreviated_interface_name }}'].{admin_mode: admin_mode, mode: mode, access_vlan: access_vlan, trunking_vlans: trunking_vlans, native_vlan: native_vlan}",
                "post_processor": "{{ obj | get_vlan_data(vlan_map, 'tagged') | tojson }}",
            },
            self.jinja_env,
            {
                "obj": "1.1.1.1",
                "original_host": "1.1.1.1",
                "vlan_map": vlan_map_post_processed,
                "current_key": "GigabitEthernet1/8",
            },
            None,
            self.logger,
        )
        expected_parsed_result = (
            [
                {
                    "access_vlan": "10",
                    "admin_mode": "trunk",
                    "mode": "down (suspended member of bundle Po8)",
                    "native_vlan": "10",
                    "trunking_vlans": ["10"],
                }
            ],
            [{"id": "10", "name": "10.39.110.0/25.LAN"}],
        )
        self.assertEqual(expected_parsed_result, actual_result)

    def test_extract_and_post_process_result_list_to_string_vios(self):
        parsed_command_output = [
            {
                "software_image": "VIOS-ADVENTERPRISEK9-M",
                "version": "15.8(3)M2",
                "release": "fc2",
                "rommon": "Bootstrap",
                "hostname": "rtr-01",
                "uptime": "1 week, 3 days, 16 hours, 11 minutes",
                "uptime_years": "",
                "uptime_weeks": "1",
                "uptime_days": "3",
                "uptime_hours": "16",
                "uptime_minutes": "11",
                "reload_reason": "Unknown reason",
                "running_image": "/vios-adventerprisek9-m",
                "hardware": ["IOSv"],
                "serial": ["991UCMIHG4UAJ1J010CQG"],
                "config_register": "0x0",
                "mac_address": [],
                "restarted": "",
            }
        ]
        actual_result = extract_and_post_process(
            parsed_command_output,
            {
                "command": "show version",
                "parser": "textfsm",
                "jpath": "[*].serial[]",
            },
            self.jinja_env,
            {"obj": "1.1.1.1", "original_host": "1.1.1.1"},
            "str",
            self.logger,
        )
        expected_parsed_result = (["991UCMIHG4UAJ1J010CQG"], "991UCMIHG4UAJ1J010CQG")
        self.assertEqual(expected_parsed_result, actual_result)
