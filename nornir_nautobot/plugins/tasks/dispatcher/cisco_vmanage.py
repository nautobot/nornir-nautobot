"""nornir dispatcher for cisco Vmanage controllers."""

from logging import Logger
from typing import Any

from nautobot.dcim.models import Controller, Device
from nornir.core.task import Task
from nornir_nautobot.plugins.tasks.dispatcher.base_controller_driver import (
    BaseControllerDriver,
)
from nornir_nautobot.utils.controller import (
    ConnectionMixin,
    format_base_url_with_endpoint,
    resolve_jmespath,
)
from requests import Response, Session


class NetmikoCiscoVmanage(BaseControllerDriver, ConnectionMixin):
    """Vmanage Controller Dispatcher class."""

    get_headers: dict[str, str] = {}
    post_headers: dict[str, str] = {}
    controller_url: str = ""
    session = None

    @classmethod
    def authenticate(cls, logger: Logger, obj: Device, task: Task) -> Any:
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
        cls.session: Session = cls.configure_session()
        if controller_group := obj.controller_managed_device_group:
            controller: Controller = controller_group.controller
            cls.controller_url = controller.external_integration.remote_url
        elif controllers := obj.controllers.all():
            for cntrlr in controllers:
                if "vmanage" in cntrlr.platform.name.lower():
                    cls.controller_url = cntrlr.external_integration.remote_url
        if not cls.controller_url:
            logger.error("Could not find the vManage URL")
            raise ValueError("Could not find the vManage URL")
        username, password = task.host.username, task.host.password
        j_security_payload = f"j_username={username}&j_password={password}"
        security_url: str = format_base_url_with_endpoint(
            base_url=cls.controller_url,
            endpoint="j_security_check",
        )
        # TODO: Change verify to true
        security_resp: Response = cls.return_response_obj(
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
        j_session_id: str = security_resp.headers.get("Set-Cookie", "")
        if not j_session_id:
            logger.error(
                "Could not find JSESSIONID from vManage controller",
            )
            raise ValueError(
                "Could not find JSESSIONID from vManage controller",
            )
        token_url: str = format_base_url_with_endpoint(
            base_url=cls.controller_url,
            endpoint="dataservice/client/token",
        )
        token_resp: str = cls.return_response_content(
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
        cls.get_headers.update(
            {
                "Cookie": j_session_id,
                "Content-Type": "application/json",
                "X-XSRF-TOKEN": str(token_resp),
            }
        )

    @classmethod
    def resolve_backup_endpoint(
        cls,
        controller_obj: Any,
        logger: Logger,
        endpoint_context: list[dict[Any, Any]],
        **kwargs: Any,
    ) -> dict[str, dict[Any, Any]]:
        """Resolve endpoint with parameters if any.

        Args:
            controller_obj (Any): Controller object or None.
            logger (Logger): Logger object.
            endpoint_context (list[dict[Any, Any]]): controller endpoint context.
            kwargs (Any): Keyword arguments.

        Returns:
            Any: Dictionary of responses.
        """
        responses: dict[str, dict[Any, Any]] = {}
        for endpoint in endpoint_context:
            api_endpoint: str = format_base_url_with_endpoint(
                base_url=cls.controller_url,
                endpoint=endpoint["endpoint"],
            )
            response = cls.return_response_content(
                session=cls.session,
                method=endpoint["method"],
                url=api_endpoint,
                headers=cls.get_headers,
                verify=False,
                logger=logger,
            )
            jpath_fields: dict[str, Any] = resolve_jmespath(
                jmespath_values=endpoint["jmespath"],
                api_response=response,
            )
            if not jpath_fields:
                logger.error(f"jmespath values not found in {response}")
                continue
            responses.update(jpath_fields)

        return responses

    # @classmethod
    # def resolve_remediation_endpoint(
    #     cls,
    #     controller_obj: Any,
    #     logger: Logger,
    #     endpoint_context: list[dict[Any, Any]],
    #     payload: dict[str, Any],
    #     **kwargs: Any,
    # ) -> list[dict[str, Any]]:
    #     """Resolve endpoint with parameters if any.

    #     Args:
    #         controller_obj (Any): Controller object or None.
    #         logger (Logger): Logger object.
    #         endpoint_context (list[dict[Any, Any]]): controller endpoint context.
    #         kwargs (Any): Keyword arguments.

    #     Returns:
    #         Any: Dictionary of responses.
    #     """
    #     aggregated_results: list[Any] = []
    #     for method_context in endpoint_context:
    #         method_callable: Optional[Callable[[Any], Any]] = _resolve_method_callable(
    #             controller_obj=controller_obj,
    #             method=method_context["endpoint"],
    #             logger=logger,
    #         )
    #         if not method_callable:
    #             logger.error(
    #                 f"The method {method_context['endpoint']} does not exist in the controller object",
    #             )
    #             continue
    #         for param in method_context["parameters"]["non_optional"]:
    #             payload.update({param: kwargs[param]})
    #         try:
    #             response: Any = method_callable(**payload)
    #         except TypeError:
    #             logger.error(
    #                 f"The params {payload} are not valid/sufficient for the {method_callable} method",
    #             )
    #             continue
    #         except Exception as e:
    #             logger.warning(
    #                 e,
    #             )
    #             continue
    #         aggregated_results.append(response)
    #     return aggregated_results
