"""API dispatcher for cisco Meraki controllers."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from logging import Logger

    from nornir.core.task import Task

from meraki import DashboardAPI

from nornir_nautobot.plugins.tasks.dispatcher.default import ApiDefault
from nornir_nautobot.utils.helpers import (
    add_api_path_to_url,
    resolve_controller_url,
    resolve_jmespath,
    resolve_params,
)


# Resolving endpoint private functions
def _resolve_method_callable(
    controller_obj: Any,
    method: str,
    logger: Logger,
) -> Callable[[Any], Any] | None:
    """Resolve method callable.

    Args:
        controller_obj (Any): Controller object, i.e. DashboardAPI for Meraki.
        method (str): 'class.method' name.
        logger (Logger): Logger object.

    Returns:
        Callable[[Any], Any] | None: Method callable or None.
    """
    cotroller_class, controller_method = method.split(sep=".")
    try:
        class_callable: Callable[[Any], Any] = getattr(
            controller_obj,
            cotroller_class,
        )
    except AttributeError:
        exc_msg: str = f"The class {cotroller_class} does not exist in the controller object"
        logger.error(exc_msg)
        return None
    try:
        method_callable: Callable[[Any], Any] = getattr(
            class_callable,
            controller_method,
        )
    except AttributeError:
        exc_msg: str = f"The method {controller_method} does not exist in the {cotroller_class} class"
        logger.error(exc_msg)
        return None
    return method_callable


def _send_call(
    method_callable: Callable[[Any], Any],
    logger: Logger,
    payload: dict[Any, Any],
) -> Any | None:
    try:
        return method_callable(**payload)
    except TypeError as e:
        exc_msg: str = f"The payload {payload} are not valid/sufficient for the {method_callable} method"
        logger.error(exc_msg)
        logger.warning(
            e,
        )
        return None
    except Exception as e:
        logger.error(e)
        return None


def _send_remediation_call(
    api_context: dict[str, Any],
    method_callable: Callable[[Any], Any],
    aggregated_results: list[Any],
    logger: Logger,
    payload: dict[Any, Any],
    **kwargs: Any,
) -> None:
    """Send remediation call.

    Args:
        api_context (dict[str, Any]): API endpoint context.
        method_callable (Callable[[Any], Any]): Method to call
        aggregated_results (list[Any]): List of aggregated results.
        logger (Logger): Logger object.
        payload (dict[Any, Any]): Payload to pass to the API call.
        kwargs (Any): Keyword arguments.
    """
    for param in api_context["parameters"]["non_optional"]:
        if not kwargs.get(param):
            logger.error(
                f"resolve_endpoint method needs '{param}' in kwargs",
            )
        payload.update({param: kwargs[param]})
    response: Any | None = _send_call(
        method_callable=method_callable,
        logger=logger,
        payload=payload,
    )
    if not response:
        return

    aggregated_results.append(response)


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

        Raises:
            ValueError: Could not find the controller API URL in config context.

        Returns:
            Any: Controller object or None.
        """
        url: str = resolve_controller_url(
            obj=obj,
            logger=logger,
            controller_type=cls.controller_type,
        )
        controller_url: str = add_api_path_to_url(
            api_path="api/v1",
            base_url=url,
        )
        api_key: str = task.host.password
        controller_obj: DashboardAPI = DashboardAPI(
            api_key=api_key,
            base_url=controller_url,
            output_log=False,
            print_console=False,
        )
        if not controller_obj:
            exc_msg: str = "Could not authenticate to the Meraki controller"
            logger.error(exc_msg)
            raise ValueError(exc_msg)
        return controller_obj

    @classmethod
    def controller_setup(
        cls,
        device_obj,
        authenticated_obj: Any,
        logger: Logger,
    ) -> dict[str, str]:
        """Setup for controller.

        Args:
            device_obj (Device): Nautobot Device object.
            authenticated_obj (Any): The controller object, i.e DashboardAPI for
                controller or None is not SDK.
            logger (Logger): Logger object.

        Returns:
            dict[str, str]: Map for controller data.

        Raises:
            ValueError: If the Meraki organization ID is not found in API response.
        """
        config_context: OrderedDict[Any, Any] = device_obj.get_config_context()
        org_id: str = config_context.get("organization_id")
        if not org_id:
            exc_msg: str = "Could not find the Meraki organization ID in API response"
            logger.error(exc_msg)
            raise ValueError(exc_msg)
        networkId = config_context.get("network_id")
        return {
            "organizationId": org_id,
            "networkId": networkId,
            "serial": device_obj.serial,
        }

    @classmethod
    def resolve_backup_endpoint(
        cls,
        authenticated_obj: Any,
        device_obj,
        logger: Logger,
        endpoint_context: list[dict[Any, Any]],
        feature_name: str,
        **kwargs: Any,
    ) -> dict[str, dict[Any, Any]]:
        """Resolve endpoint with parameters if any.

        Args:
            authenticated_obj (Any): Controller object or None.
            device_obj (Device): Nautobot Device object.
            logger (Logger): Logger object.
            endpoint_context (list[dict[Any, Any]]): controller endpoint context.
            feature_name (str): Feature name being collected.
            kwargs (Any): Keyword arguments.

        Returns:
            Any: Dictionary of responses.

        Raises:
            ValueError: If required parameters are missing in kwargs.
            TypeError: If response types are inconsistent (not all list or all dict).
        """
        try:
            organization_id: str = kwargs["organizationId"]
            network_id: str = kwargs["networkId"]
        except KeyError as exc:
            missing: str = exc.args[0]
            exc_msg: str = f"resolve_endpoint() needs '{missing}' in kwargs"
            raise ValueError(exc_msg) from exc
        responses: dict[str, dict[Any, Any]] | list[Any] | None = None
        param_mapper: dict[str, str] = {
            "organizationId": organization_id,
            "networkId": network_id,
        }
        for endpoint in endpoint_context:
            method_callable: Callable[[Any], Any] | None = _resolve_method_callable(
                controller_obj=authenticated_obj,
                method=endpoint["endpoint"],
                logger=logger,
            )
            if not method_callable:
                logger.warning(
                    msg=f"The method {endpoint['endpoint']} could not be resolved",
                )
                continue
            params: dict[Any, Any] = resolve_params(
                parameters=endpoint.get("parameters"),
                param_mapper=param_mapper,
            )
            response: Any | None = _send_call(
                method_callable=method_callable,
                logger=logger,
                payload=params,
            )
            if not response:
                logger.warning(
                    msg=f"The API call to {endpoint['endpoint']} returned no response",
                )
                continue
            jpath_fields: dict[str, Any] | list[dict[str, Any]] = resolve_jmespath(
                jmespath_values=endpoint["jmespath"],
                api_response=response,
                logger=logger,
            )
            if not jpath_fields:
                logger.error(f"jmespath values not found in {response}")
                continue
            if isinstance(jpath_fields, list):
                if responses is None:
                    responses = jpath_fields
                    continue
                if not isinstance(responses, list):
                    exc_msg: str = f"All responses should be list but got {type(responses)}"
                    raise TypeError(exc_msg)
                responses.extend(jpath_fields)
            else:
                if responses is None:
                    responses = jpath_fields
                    continue
                if not isinstance(responses, dict):
                    exc_msg: str = f"All responses should be dict but got {type(responses)}"
                    raise TypeError(exc_msg)
                responses.update(jpath_fields)

        if responses:
            return responses
        logger.error(
            f"No valid responses found for the {feature_name} endpoints",
        )
        return {}

    @classmethod
    def resolve_remediation_endpoint(
        cls,
        authenticated_obj: Any,
        device_obj,
        logger: Logger,
        endpoint_context: list[dict[Any, Any]],
        payload: dict[Any, Any] | list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Resolve endpoint with parameters if any.

        Args:
            authenticated_obj (Any): Controller object, i.e. Meraki Dashboard object or None.
            device_obj (Device): Nautobot Device object.
            logger (Logger): Logger object.
            endpoint_context (list[dict[Any, Any]]): controller endpoint config context.
            payload (dict[Any, Any] | list[dict[str, Any]]): Payload to pass to the API call.
            kwargs (Any): Keyword arguments.

        Returns:
            list[dict[str, Any]]: List of API responses.
        """
        aggregated_results: list[Any] = []
        for api_context in endpoint_context:
            method_callable: Callable[[Any], Any] | None = _resolve_method_callable(
                controller_obj=authenticated_obj,
                method=api_context["endpoint"],
                logger=logger,
            )
            if not method_callable:
                logger.error(
                    f"The method {api_context['endpoint']} does not exist in the controller object",
                )
                continue
            if isinstance(payload, dict):
                _send_remediation_call(
                    api_context=api_context,
                    method_callable=method_callable,
                    aggregated_results=aggregated_results,
                    logger=logger,
                    payload=payload,
                    **kwargs,
                )
            if isinstance(payload, list):
                for item in payload:
                    _send_remediation_call(
                        api_context=api_context,
                        method_callable=method_callable,
                        aggregated_results=aggregated_results,
                        logger=logger,
                        payload=item,
                        **kwargs,
                    )
        return aggregated_results
