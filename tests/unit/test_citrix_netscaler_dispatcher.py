"""Unit tests for the Citrix Netscaler dispatcher."""

import unittest
from logging import Logger, getLogger
from typing import Any
from unittest.mock import MagicMock, patch

from nornir_nautobot.plugins.tasks.dispatcher.citrix_netscaler import ApiCitrixNetscaler
from tests.unit.conftest import get_json_fixture


class TestCitrixNetscalerDispatcher(unittest.TestCase):
    """Test the Citrix Netscaler dispatcher."""

    base_import_path: str = "nornir_nautobot.plugins.tasks.dispatcher"

    @patch(f"{base_import_path}.citrix_netscaler.use_snip_hostname")
    @patch.object(target=ApiCitrixNetscaler, attribute="configure_session")
    def test_authenticate(
        self,
        mock_configure_session,
        mock_use_snip_hostname,
    ) -> None:
        """Test the authentication process for the Citrix Netscaler dispatcher."""
        ApiCitrixNetscaler.get_headers = {}
        mock_use_snip_hostname.return_value = "https://netscaler.com"
        mock_configure_session.return_value = MagicMock()
        logger: Logger = getLogger(name="test")
        obj: MagicMock = MagicMock()
        task: MagicMock = MagicMock()
        task.host.password = "mock_api_key"
        task.host.username = "mock_api_username"

        ApiCitrixNetscaler.authenticate(
            logger=logger,
            obj=obj,
            task=task,
        )

        mock_use_snip_hostname.assert_called_once()
        mock_configure_session.assert_called_once()
        self.assertIn("X-NITRO-USER", ApiCitrixNetscaler.get_headers)
        self.assertIn("X-NITRO-PASS", ApiCitrixNetscaler.get_headers)

    @patch(f"{base_import_path}.citrix_netscaler.use_snip_hostname")
    @patch.object(target=ApiCitrixNetscaler, attribute="configure_session")
    def test_authenticate_no_snip_hostname(
        self,
        mock_configure_session,
        mock_use_snip_hostname,
    ) -> None:
        """Test authentication when use_snip_hostname returns an empty string."""
        ApiCitrixNetscaler.get_headers = {}
        mock_use_snip_hostname.return_value = ""
        logger: Logger = getLogger(name="test")
        obj: MagicMock = MagicMock()
        task: MagicMock = MagicMock()
        task.host.password = "mock_api_key"
        task.host.username = "mock_api_username"

        ApiCitrixNetscaler.authenticate(
            logger=logger,
            obj=obj,
            task=task,
        )

        mock_use_snip_hostname.assert_called_once()
        mock_configure_session.assert_called_once()
        self.assertIn("X-NITRO-USER", ApiCitrixNetscaler.get_headers)
        self.assertEqual(ApiCitrixNetscaler.get_headers["X-NITRO-USER"], "mock_api_username")

    @patch(f"{base_import_path}.citrix_netscaler.use_snip_hostname")
    @patch.object(target=ApiCitrixNetscaler, attribute="configure_session")
    def test_authenticate_no_username(
        self,
        mock_configure_session,
        mock_use_snip_hostname,
    ) -> None:
        """Test authentication when username is missing."""
        ApiCitrixNetscaler.get_headers = {}
        mock_use_snip_hostname.return_value = "https://netscaler.com"
        logger: Logger = getLogger(name="test")
        obj: MagicMock = MagicMock()
        task: MagicMock = MagicMock()
        task.host.password = "mock_api_key"
        task.host.username = ""

        ApiCitrixNetscaler.authenticate(
            logger=logger,
            obj=obj,
            task=task,
        )

        mock_use_snip_hostname.assert_called_once()
        mock_configure_session.assert_called_once()
        self.assertIn("X-NITRO-USER", ApiCitrixNetscaler.get_headers)
        self.assertEqual(ApiCitrixNetscaler.get_headers["X-NITRO-USER"], "")

    @patch(f"{base_import_path}.citrix_netscaler.use_snip_hostname")
    @patch.object(target=ApiCitrixNetscaler, attribute="configure_session")
    def test_authenticate_no_password(
        self,
        mock_configure_session,
        mock_use_snip_hostname,
    ) -> None:
        """Test authentication when password is missing."""
        ApiCitrixNetscaler.get_headers = {}
        mock_use_snip_hostname.return_value = "https://netscaler.com"
        logger: Logger = getLogger(name="test")
        obj: MagicMock = MagicMock()
        task: MagicMock = MagicMock()
        task.host.password = ""
        task.host.username = "mock_api_username"

        ApiCitrixNetscaler.authenticate(
            logger=logger,
            obj=obj,
            task=task,
        )

        mock_use_snip_hostname.assert_called_once()
        mock_configure_session.assert_called_once()
        self.assertIn("X-NITRO-PASS", ApiCitrixNetscaler.get_headers)
        self.assertEqual(ApiCitrixNetscaler.get_headers["X-NITRO-PASS"], "")

    @patch.object(target=ApiCitrixNetscaler, attribute="url", new="https://netscaler.com")
    @patch.object(target=ApiCitrixNetscaler, attribute="session", new_callable=MagicMock)
    @patch.object(target=ApiCitrixNetscaler, attribute="configure_session", new=MagicMock())
    @patch.object(target=ApiCitrixNetscaler, attribute="return_response_content")
    def test_resolve_backup_endpoint(self, mock_return_response_content, mock_session) -> None:
        """Test the authentication process for the Citrix Netscaler dispatcher."""
        # Setup mocks
        mock_session.return_value = MagicMock()
        mock_return_response_content.return_value = get_json_fixture(
            folder="api_responses",
            file_name="full_netscaler_response.json",
        )
        logger: Logger = getLogger(name="test")
        config_context: dict[Any, Any] = get_json_fixture(
            folder="config_context",
            file_name="backup_netscaler_context.json",
        )

        # Call authenticate
        device_obj: MagicMock = MagicMock()
        responses: dict[str, dict[Any, Any]] | list[Any] = ApiCitrixNetscaler.resolve_backup_endpoint(
            device_obj=device_obj,
            logger=logger,
            endpoint_context=config_context.get("ntp_backup"),
            feature_name="ntp_backup",
        )
        expected_response: dict[str, Any] = get_json_fixture(
            folder="api_responses",
            file_name="netscaler_backup.json",
        )

        # Assertions
        self.assertIsNotNone(obj=responses)
        self.assertEqual(responses, expected_response)

    @patch.object(target=ApiCitrixNetscaler, attribute="url", new="https://netscaler.com")
    @patch.object(target=ApiCitrixNetscaler, attribute="session", new_callable=MagicMock)
    @patch.object(target=ApiCitrixNetscaler, attribute="configure_session", new=MagicMock())
    @patch.object(target=ApiCitrixNetscaler, attribute="return_response_content")
    def test_resolve_backup_endpoint_no_response(self, mock_return_response_content, mock_session) -> None:
        """Test resolve_backup_endpoint when no response is returned."""
        mock_session.return_value = MagicMock()
        mock_return_response_content.return_value = None
        logger: Logger = getLogger(name="test")
        config_context: dict[Any, Any] = get_json_fixture(
            folder="config_context",
            file_name="backup_netscaler_context.json",
        )

        device_obj: MagicMock = MagicMock()
        responses: dict[str, dict[Any, Any]] | list[Any] = ApiCitrixNetscaler.resolve_backup_endpoint(
            device_obj=device_obj,
            logger=logger,
            endpoint_context=config_context.get("ntp_backup"),
            feature_name="ntp_backup",
        )

        self.assertEqual(responses, {})

    @patch.object(target=ApiCitrixNetscaler, attribute="url", new="https://netscaler.com")
    @patch.object(target=ApiCitrixNetscaler, attribute="session", new_callable=MagicMock)
    @patch.object(target=ApiCitrixNetscaler, attribute="configure_session", new=MagicMock())
    @patch.object(target=ApiCitrixNetscaler, attribute="return_response_content")
    def test_resolve_backup_endpoint_jmespath_not_found(self, mock_return_response_content, mock_session) -> None:
        """Test resolve_backup_endpoint when jmespath values are not found."""
        mock_session.return_value = MagicMock()
        mock_return_response_content.return_value = {"some_key": "some_value"}
        logger: Logger = getLogger(name="test")
        config_context: dict[Any, Any] = get_json_fixture(
            folder="config_context",
            file_name="backup_netscaler_context.json",
        )

        device_obj: MagicMock = MagicMock()
        responses: dict[str, dict[Any, Any]] | list[Any] = ApiCitrixNetscaler.resolve_backup_endpoint(
            device_obj=device_obj,
            logger=logger,
            endpoint_context=config_context.get("ntp_backup"),
            feature_name="ntp_backup",
        )

        self.assertEqual(responses, {})
