"""nornir dispatcher for cisco Vmanage controllers."""

from logging import Logger
from typing import Any, Callable, Optional, OrderedDict

from nautobot.dcim.models import Controller, Device
from nornir.core.task import Task
from nornir_nautobot.plugins.tasks.dispatcher.base_controller_driver import (
    BaseControllerDriver,
    ConnectionMixin,
    resolve_jmespath,
    resolve_params,
)
from requests import Response, Session


# Resolving endpoint private functions
def _resolve_method_callable(
    controller_obj: Any,
    method: str,
    logger: Logger,
) -> Optional[Callable[[Any], Any]]:
    """Resolve method callable.

    Args:
        controller_obj (Any): Controller object, i.e. DashboardAPI for Meraki.
        method (str): 'class.method' name.
        logger (Logger): Logger object.

    Returns:
        Optional[Callable[[Any], Any]]: Method callable or None.
    """
    cotroller_class, controller_method = method.split(sep=".")
    try:
        class_callable: Callable[[Any], Any] = getattr(
            controller_obj,
            cotroller_class,
        )
    except AttributeError:
        logger.error(
            f"The class {cotroller_class} does not exist in the controller object",
        )
        return
    try:
        method_callable: Callable[[Any], Any] = getattr(
            class_callable,
            controller_method,
        )
    except AttributeError:
        logger.error(
            f"The method {controller_method} does not exist in the {cotroller_class} class",
        )
        return
    return method_callable


class NetmikoCiscoVmanage(BaseControllerDriver, ConnectionMixin):
    """Vmanage Controller Dispatcher class."""

    session: Session = cls.configure_session()
    get_headers: dict[str, str] = {}
    post_headers: dict[str, str] = {}

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
        controller_url: str = ""
        if controller_group := obj.controller_managed_device_group:
            controller: Controller = controller_group.controller
            controller_url = controller.external_integration.remote_url
        elif controllers := obj.controllers.all():
            for cntrlr in controllers:
                if "vmanage" in cntrlr.platform.name.lower():
                    controller_url = cntrlr.external_integration.remote_url
        if not controller_url:
            logger.error("Could not find the Meraki Dashboard API URL")
            raise ValueError("Could not find the Meraki Dashboard API URL")
        username, password = task.host.username, task.host.password
        j_security_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        j_security_payload = f"j_username={username}&j_password={password}"
        # TODO: Change verify to true
        security_resp: Response = cls.return_response_obj(
            session=cls.session,
            method="POST",
            url=f"{controller_url}/j_security_check",
            headers=j_security_headers,
            body=j_security_payload,
            verify=False,
        )
        j_session_id: str = security_resp.headers.get("Set-Cookie", "")
        if not j_session_id:
            logger.error(
                "Could not find getJSESSIONID from vManage controller",
            )
            raise ValueError(
                "Could not find getJSESSIONID from vManage controller",
            )
        token_headers = {
            "Cookie": j_session_id,
            "Content-Type": "application/json",
        }
        # TODO: Need to make a method to determine if there is a trailing forward slash in the URL
        token_resp: str = cls.return_response_content(
            session=cls.session,
            method="GET",
            url=f"{controller_url}dataservice/client/token",
            headers=token_headers,
            verify=False,
        )
        cls.get_headers.update(
            {
                "Cookie": j_session_id,
                "Content-Type": "application/json",
                "X-XSRF-TOKEN": str(token_resp),
            }
        )

    @classmethod
    def controller_setup(
        cls,
        device_obj: Device,
        controller_obj: Any,
        logger: Logger,
    ) -> dict[str, str]:
        """Setup for controller.

        Args:
            device_obj (Device): Nautobot Device object.
            controller_obj (Any): The controller object, i.e DashboardAPI for
                controller or None is not SDK.
            logger (Logger): Logger object.

        Returns:
            dict[str, str]: Map for controller data.
        """
        config_context: OrderedDict[Any, Any] = device_obj.get_config_context()
        org_id: str = config_context.get("organization_id")
        if not org_id:
            logger.error("Could not find the Meraki organization ID in API response")
            raise ValueError(
                "Could not find the Meraki organization ID in API response"
            )
        networkId = config_context.get("network_id")
        return {
            "organizationId": org_id,
            "networkId": networkId,
            "serial": device_obj.serial,
        }

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
        try:
            organization_id: str = kwargs["organizationId"]
            network_id: str = kwargs["networkId"]
        except KeyError as exc:
            missing: str = exc.args[0]
            raise ValueError(
                f"resolve_endpoint() needs '{missing}' in kwargs",
            ) from exc
        responses: dict[str, dict[Any, Any]] = {}
        param_mapper: dict[str, str] = {
            "organizationId": organization_id,
            "networkId": network_id,
        }
        for endpoint in endpoint_context:
            method_callable: Optional[Callable[[Any], Any]] = _resolve_method_callable(
                controller_obj=controller_obj,
                method=endpoint["method"],
                logger=logger,
            )
            if not method_callable:
                continue
            params: dict[Any, Any] = resolve_params(
                parameters=endpoint.get("parameters"),
                param_mapper=param_mapper,
            )
            try:
                response: Any = method_callable(**params)
            except TypeError as e:
                logger.error(
                    f"The params {params} are not valid/sufficient for the {method_callable} method",
                )
                logger.warning(
                    e,
                )
                continue
            except Exception as e:
                logger.error(e)
                continue
            jpath_fields: dict[str, Any] = resolve_jmespath(
                jmespath_values=endpoint["jmespath"],
                api_response=response,
            )
            if not jpath_fields:
                logger.error(f"jmespath values not found in {response}")
                continue
            responses.update(jpath_fields)

        return responses

    @classmethod
    def resolve_remediation_endpoint(
        cls,
        controller_obj: Any,
        logger: Logger,
        endpoint_context: list[dict[Any, Any]],
        payload: dict[str, Any],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Resolve endpoint with parameters if any.

        Args:
            controller_obj (Any): Controller object or None.
            logger (Logger): Logger object.
            endpoint_context (list[dict[Any, Any]]): controller endpoint context.
            kwargs (Any): Keyword arguments.

        Returns:
            Any: Dictionary of responses.
        """
        aggregated_results: list[Any] = []
        for method_context in endpoint_context:
            method_callable: Optional[Callable[[Any], Any]] = _resolve_method_callable(
                controller_obj=controller_obj,
                method=method_context["method"],
                logger=logger,
            )
            if not method_callable:
                logger.error(
                    f"The method {method_context['method']} does not exist in the controller object",
                )
                continue
            for param in method_context["parameters"]["non_optional"]:
                payload.update({param: kwargs[param]})
            try:
                response: Any = method_callable(**payload)
            except TypeError:
                logger.error(
                    f"The params {payload} are not valid/sufficient for the {method_callable} method",
                )
                continue
            except Exception as e:
                logger.warning(
                    e,
                )
                continue
            aggregated_results.append(response)
        return aggregated_results
