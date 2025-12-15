"""Base API dispatcher for API supported devices."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from logging import Logger

    from requests import Session

from nornir.core.task import Result, Task

from nornir_nautobot.plugins.tasks.dispatcher.default import DispatcherMixin
from nornir_nautobot.utils.base_connection import ConnectionMixin
from nornir_nautobot.utils.helpers import (
    format_base_url_with_endpoint,
    render_jinja_template,
    resolve_jmespath,
    resolve_query,
)


class ApiBaseDispatcher(DispatcherMixin, ConnectionMixin, ABC):
    """API Base Dispatcher class."""

    get_headers: dict[str, str] = {}
    post_headers: dict[str, str] = {}
    url: str = ""
    session: Optional[Session] = None
    controller_type: str = ""

    @classmethod
    def _render_uri_template(
        cls,
        obj,
        logger: Logger,
        template: str,
    ) -> str:
        """Render URI template.

        Args:
            obj (Device): The Device object from Nautobot.
            logger (Logger): Logger to log error messages to.
            template (str): A URI template to be rendered.

        Returns:
            str: The ``template`` rendered.
        """
        return render_jinja_template(obj=obj, logger=logger, template=template)

    @classmethod
    def _cc_feature_name_parser(cls, feature_name: str) -> str:
        """Feature name parser.

        Args:
            feature_name (str): The feature name from config context.

        Returns:
            str: Parsed feature name.
        """
        if "_" in feature_name:
            feat = feature_name.rsplit(sep="_", maxsplit=1)[0]
        elif "-" in feature_name:
            feat = feature_name.rsplit(sep="-", maxsplit=1)[0]
        else:
            feat = feature_name.rsplit(sep=" ", maxsplit=1)[0]
        return feat.lower().strip().replace("-", "_").replace(" ", "_")

    @classmethod
    @abstractmethod
    def authenticate(cls, logger: Logger, obj, task: Task) -> Any:
        """Authenticate to controller.

        Args:
            logger (Logger): Logger object.
            obj (Device): Device object.
            task (Task): Nornir Task object.

        Returns:
            Any: Controller object or None.
        """

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
        """
        # Overwrite if needed in child class
        return {}

    @classmethod
    def resolve_backup_endpoint(
        cls,
        authenticated_obj: Any,
        device_obj,
        logger: Logger,
        endpoint_context: list[dict[Any, Any]],
        feature_name: str,
        **kwargs: Any,
    ) -> Union[list[Any], dict[str, dict[Any, Any]]]:
        """Resolve endpoint with parameters if any.

        Args:
            authenticated_obj (Any): Controller object or None.
            device_obj (Device): Nautobot Device object.
            logger (Logger): Logger object.
            endpoint_context (list[dict[Any, Any]]): controller endpoint context.
            feature_name (str): Feature name being collected.
            kwargs (Any): Keyword arguments.

        Returns:
            Union[list[Any], dict[str, dict[Any, Any]]]: Dictionary of responses.

        Raises:
            TypeError: If the type of responses is inconsistent (list vs dict).
        """
        responses: dict[str, dict[Any, Any]] | list[Any] | None = None
        for endpoint in endpoint_context:
            uri: str = cls._render_uri_template(
                obj=device_obj,
                logger=logger,
                template=endpoint["endpoint"],
            )
            api_endpoint: str = format_base_url_with_endpoint(
                base_url=cls.url,
                endpoint=uri,
            )
            if endpoint.get("query"):
                api_endpoint = resolve_query(
                    api_endpoint=api_endpoint,
                    query=endpoint["query"],
                )
            response: Any = cls.return_response_content(
                session=cls.session,
                method=endpoint["method"],
                url=api_endpoint,
                headers=cls.get_headers,
                verify=False,
                logger=logger,
            )
            if response is None:
                logger.error(
                    f"Error in API call to {api_endpoint}: No response",
                )
                continue
            jpath_fields: dict[Any, Any] | list[Any] = resolve_jmespath(
                jmespath_values=endpoint["jmespath"],
                api_response=response,
                logger=logger,
            )
            if not jpath_fields or (isinstance(jpath_fields, dict) and all(v is None for v in jpath_fields.values())):
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
            elif isinstance(jpath_fields, dict):
                if responses is None:
                    responses = jpath_fields
                if not isinstance(responses, dict):
                    exc_msg: str = f"All responses should be dict but got {type(responses)}"
                    raise TypeError(exc_msg)
                responses.update(jpath_fields)
            else:
                logger.error(
                    f"Unexpected jmespath response type: {type(jpath_fields)}",
                )

        if responses:
            return responses
        logger.error(
            f"No valid responses found for the {feature_name} endpoints",
        )
        return {}

    @classmethod
    def get_config(  # pylint: disable=R0913,R0914
        cls,
        task: Task,
        logger: Logger,
        obj,
        backup_file: str,
        remove_lines: list[str],
        substitute_lines: list[str],
    ) -> Result | None:
        """Get the latest configuration from controller.

        Args:
            task (Task): Nornir Task.
            logger (Logger): Nautobot logger.
            obj (Device): Device object.
            backup_file (str): Backup file location.
            remove_lines (list[str]): Lines to remove from the configuration.
            substitute_lines (list[str]): Lines to replace in the configuration.

        Returns:
            None | Result: Nornir Result object with a dict as a result
                containing the running configuration or None.

        Raises:
            ValueError: If controller endpoints cannot be found in the config context.
        """
        cfg_cntx: OrderedDict[Any, Any] = obj.get_config_context()
        authenticated_obj: Any = cls.authenticate(
            logger=logger,
            obj=obj,
            task=task,
        )
        logger.info(
            f"Authenticated to {obj.name} platform: {obj.platform.name}",
        )
        controller_dict: dict[str, str] = cls.controller_setup(
            device_obj=obj,
            authenticated_obj=authenticated_obj,
            logger=logger,
        )
        feature_endpoints: list[str] = cfg_cntx.get("backup_endpoints", "")
        if not feature_endpoints:
            exc_msg: str = "Could not find the controller endpoints"
            logger.error(exc_msg)
            raise ValueError(exc_msg)
        _running_config: dict[str, dict[Any, Any]] = {}
        logger.info(f"Collecting feature endpoint backups for {obj.name}")
        for feature in feature_endpoints:
            endpoints: list[dict[Any, Any]] = cfg_cntx.get(feature, "")
            feature_name: str = cls._cc_feature_name_parser(
                feature_name=feature,
            )
            if not endpoints:
                logger.error(
                    f"Could not find the endpoint context for {feature} in the config context",
                )
                continue
            feature_response_raw: dict[str, dict[Any, Any]] | list[Any] = cls.resolve_backup_endpoint(
                authenticated_obj=authenticated_obj,
                device_obj=obj,
                logger=logger,
                endpoint_context=endpoints,
                feature_name=feature_name,
                **controller_dict,
            )
            if not feature_response_raw:
                logger.error(
                    f"Could not fetch {feature_name} configuration from controller using context {feature} ",
                )
                continue
            if isinstance(feature_response_raw, dict):
                feature_response: dict[str, dict[Any, Any]] = feature_response_raw
            elif isinstance(feature_response_raw, list):
                feature_response: dict[str, dict[Any, Any]] = {str(i): v for i, v in enumerate(feature_response_raw)}
            else:
                logger.error(f"Unexpected type for feature_response: {type(feature_response_raw)}")
                continue
            _running_config.update({feature_name: feature_response})
        logger.info(
            f"Finished collecting feature endpoint backups for {obj.name}",
        )
        processed_config: str = cls._process_config(
            logger=logger,
            running_config=json.dumps(obj=_running_config, indent=4),
            remove_lines=remove_lines,
            substitute_lines=substitute_lines,
            backup_file=backup_file,
        )
        return Result(host=task.host, result={"config": processed_config})

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
        if not cls.session:
            logger.error("No session available for API calls")
            return aggregated_results
        for endpoint in endpoint_context:
            uri: str = cls._render_uri_template(
                obj=device_obj,
                logger=logger,
                template=endpoint["endpoint"],
            )
            api_endpoint: str = format_base_url_with_endpoint(
                base_url=cls.url,
                endpoint=uri,
            )
            req_params: list[str] = (
                endpoint["parameters"]["non_optional"]
                if "parameters" in endpoint and "non_optional" in endpoint["parameters"]
                else []
            )
            if isinstance(payload, dict):
                payload_copy = payload.copy()
                for param in req_params:
                    if not kwargs:
                        continue
                    if not kwargs.get(param):
                        logger.error(
                            "resolve_endpoint method needs '%s' in kwargs",
                            param,
                        )
                    elif kwargs.get(param):
                        payload_copy.update({param: kwargs[param]})
                response: Any = cls.return_response_content(
                    session=cls.session,
                    method=endpoint["method"],
                    url=api_endpoint,
                    headers=cls.get_headers,
                    verify=False,
                    logger=logger,
                    body=payload_copy,
                )
                if not response:
                    logger.error(
                        "Error in API call to %s: No response",
                        api_endpoint,
                    )
                    continue
                aggregated_results.append(response)
            elif isinstance(payload, list):
                for item in payload:
                    if not isinstance(item, dict):
                        continue
                    item_copy = item.copy()
                    for param in req_params:
                        if not kwargs:
                            continue
                        if not kwargs.get(param):
                            logger.error(
                                "resolve_endpoint method needs '%s' in kwargs",
                                param,
                            )
                        else:
                            item_copy.update({param: kwargs[param]})
                    response: Any = cls.return_response_content(
                        session=cls.session,
                        method=endpoint["method"],
                        url=api_endpoint,
                        headers=cls.get_headers,
                        verify=False,
                        logger=logger,
                        body=item_copy,
                    )
                    if not response:
                        logger.error(
                            "Error in API call to %s: No response",
                            api_endpoint,
                        )
                        continue
                    aggregated_results.append(response)
        return aggregated_results

    @classmethod
    def merge_config(  # pylint: disable=too-many-positional-arguments
        cls,
        task: Task,
        logger,
        obj,
        config: str,
        can_diff: bool = True,
    ) -> Result:
        """Send configuration to merge on the device.

        Args:
            task (Task): Nornir Task.
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            config (str): The remediation payload.
            can_diff (bool, optional): Can diff the config. Defaults to True.

        Returns:
            Result: Nornir Result object with a dict as a result containing what changed and the result of the push.

        Raises:
            ValueError: If controller endpoints cannot be found in the config context.
        """
        if isinstance(config, str):
            config: dict[Any, Any] = json.loads(config)
        logger.info(
            "Config merge via controller dispatcher starting",
            extra={"object": obj},
        )
        cfg_cntx: OrderedDict[Any, Any] = obj.get_config_context()
        # The above Python code snippet is performing the following actions:
        authenticated_obj: Any = cls.authenticate(
            logger=logger,
            obj=obj,
            task=task,
        )
        controller_dict: dict[str, str] = cls.controller_setup(
            device_obj=obj,
            authenticated_obj=authenticated_obj,
            logger=logger,
        )
        aggregated_results: list[list[dict[str, Any]]] = []
        feature_endpoints: str = cfg_cntx.get("remediation_endpoints", "")
        if not feature_endpoints:
            exc_msg: str = "Could not find the controller endpoints"
            logger.error(exc_msg)
            raise ValueError(exc_msg)
        for remediation_endpoint in config:
            if f"{remediation_endpoint}_remediation" not in feature_endpoints:
                logger.error(
                    f"Could not find the remediation endpoint: {remediation_endpoint}_remediation in {feature_endpoints}",
                    extra={"object": obj},
                )
                continue
            if not cfg_cntx.get(f"{remediation_endpoint}_remediation", ""):
                logger.error(
                    f"Could not find the remediation endpoint: {remediation_endpoint}_remediation in the config context",
                    extra={"object": obj},
                )
                continue
            try:
                aggregated_results.append(
                    cls.resolve_remediation_endpoint(
                        authenticated_obj=authenticated_obj,
                        logger=logger,
                        endpoint_context=cfg_cntx[f"{remediation_endpoint}_remediation"],
                        payload=config[remediation_endpoint],
                        device_obj=obj,
                        **controller_dict,
                    ),
                )
            except NotImplementedError:
                logger.error("resolve_remediation_endpoint was not overriden.")
        if can_diff:
            logger.info(f"result: {aggregated_results}", extra={"object": obj})
            result: dict[str, Any] = {
                "changed": bool(aggregated_results),
                "result": aggregated_results,
                "failed": False,
            }
        else:
            result: dict[str, Any] = {
                "changed": bool(aggregated_results),
                "result": "Hidden to protect sensitive information",
                "failed": False,
            }

        logger.info("Config merge ended", extra={"object": obj})
        final_result: Result = Result(host=task.host, result=result)
        final_result.changed = True
        final_result.failed = False
        return final_result
