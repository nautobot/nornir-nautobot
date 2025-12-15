"""Netmiko dispatcher for cisco vManage controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from logging import Logger

    from nornir.core.task import Task
    from requests import Response, Session

from nornir_nautobot.plugins.tasks.dispatcher.api_base_dispatcher import (
    ApiBaseDispatcher,
)
from nornir_nautobot.utils.helpers import (
    format_base_url_with_endpoint,
    resolve_controller_url,
)


class NetmikoCiscoVmanage(ApiBaseDispatcher):
    """Vmanage Controller Dispatcher class."""

    controller_type: str = "vmanage"

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
        j_security_payload = f"j_username={username}&j_password={password}"
        security_url: str = format_base_url_with_endpoint(
            base_url=cls.url,
            endpoint="j_security_check",
        )
        # TODO: Change verify to true
        cls.session: Session = cls.configure_session()
        security_resp: Optional[Response] = cls.return_response_obj(
            session=cls.session,
            method="POST",
            url=security_url,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            logger=logger,
            body=j_security_payload,
            verify=False,
        )
        if not security_resp or not security_resp.headers.get("Set-Cookie"):
            exc_msg: str = "Could not generate vManage cookie. Please check the credentials and try again."
            logger.error(exc_msg)
            raise ValueError(exc_msg)
        logger.info("Successfully generated vManage cookie.")
        j_session_id: str = security_resp.headers.get("Set-Cookie", "")
        token_url: str = format_base_url_with_endpoint(
            base_url=cls.url,
            endpoint="dataservice/client/token",
        )
        token_resp: Any = cls.return_response_content(
            session=cls.session,
            method="GET",
            url=token_url,
            headers={
                "Cookie": j_session_id,
                "Content-Type": "application/json",
            },
            verify=False,
            logger=logger,
        )
        if not token_resp:
            exc_msg: str = "Could not generate vManage XSRF token."
            logger.error(exc_msg)
            raise ValueError(exc_msg)
        cls.get_headers = {
            "Cookie": j_session_id,
            "Content-Type": "application/json",
            "X-XSRF-TOKEN": str(token_resp),
        }
