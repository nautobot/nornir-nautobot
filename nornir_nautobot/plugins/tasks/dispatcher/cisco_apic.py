"""API dispatcher for cisco APIC controllers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from logging import Logger

    from nornir.core.task import Task
    from requests import Session


from nornir_nautobot.plugins.tasks.dispatcher.default import ApiDefault
from nornir_nautobot.utils.helpers import (
    format_base_url_with_endpoint,
    resolve_controller_url,
)


class ApiCiscoApic(ApiDefault):
    """APIC Controller Dispatcher class."""

    controller_type: str = "apic"

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
        cls.url: str = resolve_controller_url(
            obj=obj,
            controller_type=cls.controller_type,
            logger=logger,
        )
        username, password = task.host.username, task.host.password
        auth_payload = {
            "aaaUser": {
                "attributes": {"name": f"{username}", "pwd": f"{password}"},
            },
        }
        auth_url: str = format_base_url_with_endpoint(
            base_url=cls.url,
            endpoint="api/aaaLogin.json",
        )
        # TODO: Change verify to true
        cls.session: Session = cls.configure_session()
        auth_resp: Any = cls.return_response_content(
            session=cls.session,
            method="POST",
            url=auth_url,
            headers={
                "Content-Type": "text/plain",
            },
            logger=logger,
            body=json.dumps(auth_payload),
            verify=False,
        )
        if not auth_resp:
            exc_msg: str = "Could not find cookie from APIC controller"
            logger.error(exc_msg)
            raise ValueError(exc_msg)
        if not auth_resp.get("imdata") or not auth_resp.get("imdata")[0]:
            exc_msg: str = "Could not find cookie from APIC controller"
            logger.error(exc_msg)
            raise ValueError(exc_msg)
        cookie: str = auth_resp.get("imdata")[0].get("aaaLogin", {}).get("attributes", {}).get("token", "")
        if not cookie:
            exc_msg: str = "Could not find cookie from APIC controller"
            logger.error(exc_msg)
            raise ValueError(exc_msg)
        cls.get_headers = {
            "Cookie": f"APIC-cookie={cookie}",
            "Content-Type": "text/plain",
        }
