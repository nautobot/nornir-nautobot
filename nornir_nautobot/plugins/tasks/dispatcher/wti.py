"""Netmiko dispatcher for cisco vManage controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from logging import Logger

    from nornir.core.task import Task
    from requests import Session

from nornir_nautobot.plugins.tasks.dispatcher.default import ApiDefault
from nornir_nautobot.utils.helpers import (
    base_64_encode_credentials,
)


class ApiWti(ApiDefault):
    """WTI Controller Dispatcher class."""

    controller_type: str = "wti"

    @classmethod
    def authenticate(cls, logger: Logger, obj, task: Task) -> Any:
        """Authenticate to controller.

        Args:
            logger (Logger): Logger object.
            obj (Device): Device object.
            task (Task): Nornir Task object.

        Raises:
            ValueError: Could not find the controller API URL in config context.

        Returns:
            Any: Controller object or None.
        """
        cls.url: str = f"https://{obj.primary_ip4.host}"
        encoded_creds: str = base_64_encode_credentials(
            username=task.host.username,
            password=task.host.password,
        )
        cls.session: Session = cls.configure_session()
        cls.get_headers = {
            "Authorization": encoded_creds,
            "Content-Type": "application/json",
        }
