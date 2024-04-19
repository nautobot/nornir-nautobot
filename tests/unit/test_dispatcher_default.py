"""Unit tests for nornir_nautobot.plugins.tasks.dispatcher.default """

import os
from unittest import TestCase
from unittest.mock import Mock, patch

import jinja2
from nornir.core.task import Task, Result
from nornir.core.exceptions import NornirSubTaskError

from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.plugins.tasks.dispatcher.default import DispatcherMixin


class TestDispatcherMixin(TestCase):
    """Tests for DispatcherMixin"""

    @classmethod
    def setUpClass(cls):
        cls.dispatcher = DispatcherMixin()
        cls.logger = Mock()

    def setUp(self):
        self.task = self.create_mock_task()
        self.obj = self.create_mock_obj()

    def set_up_jinja(self):
        """Set up jinja template variables"""
        self.task.host = {"hostname": "test_hostname"}
        self.jinja_template = "test_template"
        self.jinja_root_path = "test_root_path"
        self.output_file_location = "test_output"
        self.jinja_filters = {"filter1": "value1"}
        self.jinja_env = Mock()

    def create_mock_task(self):
        """Create a mock task object"""
        task = Mock(spec=Task)
        task.host = Mock()
        task.host.hostname = "test_hostname"
        task.host.username = "test_username"
        task.host.password = "test_password"
        task.run.return_value = [Result(host=task.host, result="test_config")]
        return task

    def create_mock_obj(self):
        """Create a mock object"""
        obj = Mock()
        obj.cf.get.return_value = 22
        return obj

    # pylint: disable=protected-access
    def test_get_hostname(self):
        hostname = self.dispatcher._get_hostname(self.task)
        self.assertEqual(hostname, "test_hostname")

    def test_get_tcp_port_custom_field(self):
        self.obj.cf.get.return_value = 8080
        tcp_port = self.dispatcher._get_tcp_port(self.obj)
        self.assertEqual(tcp_port, 8080)

    def test_get_tcp_port_config_context(self):
        self.obj.cf.get.return_value = None
        self.obj.get_config_context.return_value = {"tcp_port": 8080}
        tcp_port = self.dispatcher._get_tcp_port(self.obj)
        self.assertEqual(tcp_port, 8080)

    def test_get_tcp_port_default(self):
        self.obj.cf.get.return_value = None
        self.obj.get_config_context.return_value = {}
        tcp_port = self.dispatcher._get_tcp_port(self.obj)
        self.assertEqual(tcp_port, 22)

    # pylint: disable=unused-argument
    @patch("nornir_nautobot.plugins.tasks.dispatcher.default.is_ip", return_value=True)
    @patch("nornir_nautobot.plugins.tasks.dispatcher.default.is_fqdn_resolvable", return_value=True)
    @patch("nornir_nautobot.plugins.tasks.dispatcher.default.socket.gethostbyname", return_value="192.168.1.1")
    @patch("nornir_nautobot.plugins.tasks.dispatcher.default.tcp_ping", return_value=True)
    def test_check_connectivity(self, mock_tcp_ping, mock_gethostbyname, mock_is_fqdn_resolvable, mock_is_ip):
        self.obj.cf.get.return_value = 22
        result = self.dispatcher.check_connectivity(self.task, self.logger, self.obj)
        self.assertEqual(result.host, self.task.host)

    # pylint: disable=unused-argument
    @patch("os.path.exists", return_value=True)
    @patch("nornir_nautobot.plugins.tasks.dispatcher.default.compliance", return_value="test_data")
    def test_compliance_config(self, mock_exists, mock_compliance):
        features = "test_features"
        backup_file = "test_backup_file"
        intended_file = "test_intended_file"
        platform = "test_platform"

        result = self.dispatcher.compliance_config(
            self.task, self.logger, self.obj, features, backup_file, intended_file, platform
        )
        self.assertEqual(result.result, {"feature_data": "test_data"})

    # pylint: disable=unused-argument
    @patch("builtins.open")
    @patch("nornir_nautobot.plugins.tasks.dispatcher.default.make_folder")
    def test_generate_config(self, mock_make_folder, mock_file_open):
        self.set_up_jinja()
        result = self.dispatcher.generate_config(
            self.task,
            self.logger,
            self.obj,
            self.jinja_template,
            self.jinja_root_path,
            self.output_file_location,
            self.jinja_filters,
            self.jinja_env,
        )

        self.assertEqual(result.host, self.task.host)
        self.assertEqual(result.result, {"config": "test_config"})
        mock_make_folder.assert_called_once_with(os.path.dirname(self.output_file_location))
        mock_file_open.assert_called_once_with(self.output_file_location, "w", encoding="utf8")

    def test_generate_config_undefined_error(self):
        self.set_up_jinja()

        self.task.run.side_effect = NornirSubTaskError(
            task=self.task, result=Mock(exception=jinja2.exceptions.UndefinedError())
        )
        with self.assertRaises(NornirNautobotException) as context:
            self.dispatcher.generate_config(
                self.task,
                self.logger,
                self.obj,
                self.jinja_template,
                self.jinja_root_path,
                self.output_file_location,
                self.jinja_filters,
                self.jinja_env,
            )
        self.assertTrue("E1010" in str(context.exception))
