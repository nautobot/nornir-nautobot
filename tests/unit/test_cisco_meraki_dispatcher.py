"""Unit tests for the Cisco Meraki dispatcher."""

import unittest
from logging import Logger, getLogger
from typing import Any
from unittest.mock import MagicMock, patch

from nornir_nautobot.plugins.tasks.dispatcher.cisco_meraki import ApiCiscoMeraki
from tests.unit.conftest import get_json_fixture


class TestCiscoMerakiDispatcher(unittest.TestCase):
    """Test the Cisco Meraki dispatcher."""

    base_import_path: str = "nornir_nautobot.plugins.tasks.dispatcher"

    @patch(f"{base_import_path}.cisco_meraki.resolve_controller_url")
    @patch(f"{base_import_path}.cisco_meraki.ApiCiscoMeraki.configure_session")
    def test_authenticate(
        self,
        mock_configure_session,
        mock_resolve_url,
    ) -> None:
        """Test the authentication process for the Cisco Meraki dispatcher."""
        # Setup mocks
        mock_resolve_url.return_value = "https://meraki.com"
        mock_configure_session.return_value = MagicMock()
        logger: Logger = getLogger(name="test")
        obj: MagicMock = MagicMock()
        task: MagicMock = MagicMock()
        task.host.password = "mock_api_key"
        task.host.username = "mock_api_username"
        ApiCiscoMeraki.authenticate(
            logger=logger,
            obj=obj,
            task=task,
        )
        mock_resolve_url.assert_called_once()
        mock_configure_session.assert_called_once()

    @patch.object(target=ApiCiscoMeraki, attribute="url", new="https://vmanage.com")
    @patch.object(target=ApiCiscoMeraki, attribute="session", new_callable=MagicMock)
    @patch.object(target=ApiCiscoMeraki, attribute="configure_session", new=MagicMock())
    @patch.object(target=ApiCiscoMeraki, attribute="return_response_content")
    def test_resolve_backup_endpoint(self, mock_return_response_content, mock_session) -> None:
        """Test the authentication process for the Cisco Meraki dispatcher."""
        # Setup mocks
        mock_session.return_value = MagicMock()
        mock_return_response_content.return_value = get_json_fixture(
            folder="api_responses",
            file_name="cisco_meraki_backup.json",
        )
        logger: Logger = getLogger(name="test")
        config_context: dict[Any, Any] = get_json_fixture(
            folder="config_context",
            file_name="backup_meraki_context.json",
        )

        device_obj: MagicMock = MagicMock()
        responses: dict[str, dict[Any, Any]] | list[Any] = ApiCiscoMeraki.resolve_backup_endpoint(
            device_obj=device_obj,
            logger=logger,
            endpoint_context=config_context.get("ntp_backup"),
            feature_name="ntp_backup",
        )
        # Assertions
        self.assertIsNotNone(obj=responses)
        self.assertIn(member="name", container=responses)
        self.assertIn(member="api", container=responses)
