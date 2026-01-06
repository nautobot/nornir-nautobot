"""API dispatcher for cisco Meraki controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nornir_nautobot.plugins.tasks.dispatcher.default import ApiDefault
from nornir_nautobot.utils.helpers import (
    resolve_controller_url,
)

if TYPE_CHECKING:
    from logging import Logger

    from nornir.core.task import Task
    from requests import Session


class ApiCiscoMeraki(ApiDefault):
    """Meraki Controller Dispatcher class."""

    controller_type = "meraki"

    @classmethod
    def authenticate(cls, logger: Logger, obj, task: Task) -> Any:
        """Authenticate to controller.

        Args:
            logger (Logger): Logger object.
            obj (Device): Device object.
            task (Task): Nornir Task object.
        """
        cls.url: str = resolve_controller_url(
            obj=obj,
            controller_type=cls.controller_type,
            logger=logger,
        )
        cls.session: Session = cls.configure_session()
        password = task.host.password
        cls.get_headers = {
            "X-Cisco-Meraki-API-Key": password,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
