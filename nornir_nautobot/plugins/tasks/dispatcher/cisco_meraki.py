"""nornir dispatcher for cisco Meraki controllers."""

from logging import Logger
from typing import Any, Callable, Optional

from meraki import DashboardAPI
from nautobot.dcim.models import Controller, Device

from netscaler_ext.plugins.tasks.dispatcher.base_controller_driver import (
    BaseControllerDriver,
    get_api_key,
    resolve_jmespath,
    resolve_params,
)


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


class NetmikoCiscoMeraki(BaseControllerDriver):
    """Meraki Controller Dispatcher class."""

    @classmethod
    def authenticate(
        cls,
        logger: Logger,
        obj: Device,
    ) -> Any:
        """Authenticate to controller.

        Args:
            config_context (OrderedDict[Any, Any]): Config context.
            logger (Logger): Logger object.
            obj (Device): Device object.

        Raises:
            ValueError: Could not find the controller API URL in config context.

        Returns:
            Any: Controller object.
        """
        controller_url: str = ""
        if controller_group := obj.controller_managed_device_group:
            controller: Controller = controller_group.controller
            controller_url = controller.external_integration.remote_url
        elif controllers := obj.controllers.all():
            for cntrlr in controllers:
                if "meraki" in cntrlr.platform.name.lower():
                    controller_url = cntrlr.external_integration.remote_url
        if not controller_url:
            logger.error("Could not find the Meraki Dashboard API URL")
            raise ValueError("Could not find the Meraki Dashboard API URL")
        api_key: str = get_api_key(secrets_group=obj.secrets_group)
        controller_obj: DashboardAPI = DashboardAPI(
            api_key=api_key,
            base_url=controller_url,
            output_log=False,
            print_console=False,
        )
        return controller_obj

    @classmethod
    def controller_setup(
        cls,
        controller_obj: Any,
        logger: Logger,
    ) -> dict[str, str]:
        """Setup for controller.

        Args:
            controller_obj (Any): The controller object, i.e DashboardAPI for Meraki.
            logger (Logger): Logger object.

        Returns:
            dict[str, str]: Map for controller data.
        """
        org_id: str = controller_obj.organizations.getOrganizations()[0].get("id", "")
        if not org_id:
            logger.error("Could not find the Meraki organization ID")
            raise ValueError("Could not find Meraki organization ID")
        networkId = ""
        return {
            "organizationId": org_id,
            "networkId": networkId,
        }

    @classmethod
    def resolve_endpoint(
        cls,
        controller_obj: Any,
        logger: Logger,
        endpoint_context: list[dict[Any, Any]],
        **kwargs: Any,
    ) -> dict[str, dict[Any, Any]]:
        """Resolve endpoint with parameters if any.

        Args:
            controller_obj (Any): Controller object.
            logger (Logger): Logger object.
            endpoint_context (list[dict[Any, Any]]): Meraki endpoint context.
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
            jpath_fields: dict[str, Any] = resolve_jmespath(
                jmespath_values=endpoint["jmespath"],
                api_response=response,
            )
            responses.update(jpath_fields)

        return responses
