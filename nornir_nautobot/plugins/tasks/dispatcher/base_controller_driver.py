"""Base nornir dispatcher for controllers."""

import json
from abc import ABC, abstractmethod
from logging import Logger
from typing import Any, Optional, OrderedDict, Union

import jmespath
from nautobot.apps.choices import (
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
)
from nautobot.dcim.models import Device
from nautobot.extras.models import SecretsGroup, SecretsGroupAssociation
from nornir.core.task import Result, Task
from nornir_nautobot.plugins.tasks.dispatcher.default import NetmikoDefault
from requests import Response, Session
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError, JSONDecodeError
from urllib3.util import Retry


class ConnectionMixin:
    """Mixin to connect to a service."""

    @classmethod
    def configure_session(cls) -> Session:
        """Configure a requests session.

        Returns:
            Session: Requests session.
        """
        session: Session = Session()
        retries = Retry(
            total=3,
            backoff_factor=10,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        session.mount(
            prefix="https://",
            adapter=HTTPAdapter(max_retries=retries),
        )
        return session

    @classmethod
    def return_response_content(
        cls,
        method: str,
        url: str,
        headers: dict[str, str],
        session: Session,
        logger: Logger,
        body: Optional[Union[dict[str, str], str]] = None,
        verify: bool = True,
    ) -> Any:
        """Create request and return response payload.

        Args:
            method (str): HTTP Method to use.
            url (str): URL to send request to.
            headers (dict): Headers to use in request.
            session (Session): Session to use.
            logger (Logger): The dispatcher's logger.
            body (Optional[Union[dict[str, str], str]]): Body of request.
            verify (bool): Verify SSL certificate.

        Returns:
            Any: API Response.

        Raises:
            requests.exceptions.HTTPError:
                If the HTTP request returns an unsuccessful status code.
        """
        try:
            with session as ses:
                response: Response = ses.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=body,
                    timeout=(50.0, 100.0),
                    verify=verify,
                )
                response.raise_for_status()
                json_response: dict[str, Any] = response.json()
                return json_response
        except JSONDecodeError:
            text_response: str = response.text
            return text_response
        except HTTPError as http_err:
            logger.error(http_err)
            return

    @classmethod
    def return_response_obj(
        cls,
        method: str,
        url: str,
        headers: dict[str, str],
        session: Session,
        body: Optional[Union[dict[str, str], str]] = None,
        verify: bool = True,
    ) -> Response:
        """Create request for authentication and return response object.

        Args:
            method (str): HTTP Method to use.
            url (str): URL to send request to.
            headers (dict): Headers to use in request.
            session (Session): Session to use.
            logger (Logger): The dispatcher's logger.
            body (Optional[Union[dict[str, str], str]]): Body of request.
            verify (bool): Verify SSL certificate.

        Returns:
            Response: API Response object.
        """
        with session as ses:
            response: Response = ses.request(
                method=method,
                url=url,
                headers=headers,
                data=body,
                timeout=(50.0, 100.0),
                verify=verify,
            )
            response.raise_for_status()
            return response


def get_api_key(secrets_group: SecretsGroup) -> str:
    """Get controller API Key.

    Args:
        secrets_group (SecretsGroup): SecretsGroup object.

    Raises:
        SecretsGroupAssociation.DoesNotExist: SecretsGroupAssociation access
            type TYPE_HTTP or secret type TYPE_TOKEN does not exist.

    Returns:
        str: API key.
    """
    try:
        api_key: str = secrets_group.get_secret_value(
            access_type=SecretsGroupAccessTypeChoices.TYPE_HTTP,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_TOKEN,
        )
    except SecretsGroupAssociation.DoesNotExist:
        api_key: str = secrets_group.get_secret_value(
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
        )
        return api_key
    return api_key


def resolve_params(
    parameters: list[str],
    param_mapper: dict[str, str],
) -> dict[Any, Any]:
    """Resolve parameters.

    Args:
        parameters (list[str]): Parameters list.
        param_mapper (dict[str, str]): Parameters mapper.

    Returns:
        dict[Any, Any]: _description_
    """
    params: dict[Any, Any] = {}
    if parameters:
        for param in parameters:
            if param.lower() not in [p.lower() for p in param_mapper]:
                continue
            for k, v in param_mapper.items():
                if k.lower() == param.lower():
                    param_key, param_value = k, v
                    params.update({param_key: param_value})
    return params


def resolve_jmespath(
    jmespath_values: list[dict[str, str]],
    api_response: Any,
) -> dict[Any, Any]:
    """Resolve jmespath.

    Args:
        jmespath_values (list[dict[str, str]]): Jmespath list.
        api_response (Any): API response.

    Returns:
        dict[str, Any]: Resolved jmespath data fields.
    """
    data_fields: dict[str, Any] = {}
    for jpath in jmespath_values:
        for key, value in jpath.items():
            j_value: Any = jmespath.search(
                expression=value,
                data=api_response,
            )
            if j_value:
                data_fields.update({key: j_value})
    return data_fields


class BaseControllerDriver(NetmikoDefault, ABC):
    """Base Controller Dispatcher class."""

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
        pass

    @classmethod
    @abstractmethod
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
        pass

    @classmethod
    @abstractmethod
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
        pass

    @classmethod
    def get_config(  # pylint: disable=R0913,R0914
        cls,
        task: Task,
        logger: Logger,
        obj: Device,
        backup_file: str,
        remove_lines: list[str],
        substitute_lines: list[str],
    ) -> Optional[Result]:
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
        """
        cfg_cntx: OrderedDict[Any, Any] = obj.get_config_context()
        controller_obj: Any = cls.authenticate(
            logger=logger,
            obj=obj,
            task=task,
        )
        controller_dict: dict[str, str] = cls.controller_setup(
            device_obj=obj,
            controller_obj=controller_obj,
            logger=logger,
        )
        feature_endpoints: str = cfg_cntx.get("backup_endpoints", "")
        if not feature_endpoints:
            logger.error("Could not find the controller endpoints")
            raise ValueError("Could not find controller endpoints")
        _running_config: dict[str, dict[Any, Any]] = {}
        for feature in feature_endpoints:
            endpoints: list[dict[Any, Any]] = cfg_cntx.get(feature, "")
            feature_name: str = cls._cc_feature_name_parser(feature_name=feature)
            feature_response: dict[str, dict[Any, Any]] = cls.resolve_backup_endpoint(
                controller_obj=controller_obj,
                logger=logger,
                endpoint_context=endpoints,
                **controller_dict,
            )
            if not feature_response:
                logger.error(
                    f"Could not fetch {feature_name} configuration from controller using context {feature} ",
                )
                continue
            _running_config.update({feature_name: feature_response})
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
        controller_obj: Any,
        logger: Logger,
        endpoint_context: list[dict[Any, Any]],
        payload: dict[str, Any],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Resolve endpoint with parameters if any.

        Args:
            controller_obj (Any): Controller object, i.e. Meraki Dashboard
                object or None.
            logger (Logger): Logger object.
            endpoint_context (list[dict[Any, Any]]): controller endpoint config context.
            payload (dict[str, Any]): Payload to pass to the API call.
            kwargs (Any): Keyword arguments.

        Returns:
            list[dict[str, Any]]: List of API responses.
        """
        raise NotImplementedError(
            "Subclasses must implement this is merge_config is being used."
        )

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
        """
        if isinstance(config, str):
            config = json.loads(config)
        logger.info(
            "Config merge via controller dispatcher starting", extra={"object": obj}
        )
        cfg_cntx: OrderedDict[Any, Any] = obj.get_config_context()
        # The above Python code snippet is performing the following actions:
        controller_obj: Any = cls.authenticate(
            logger=logger,
            obj=obj,
        )
        controller_dict: dict[str, str] = cls.controller_setup(
            device_obj=obj,
            controller_obj=controller_obj,
            logger=logger,
        )
        aggregated_results: list[list[dict[str, Any]]] = []
        feature_endpoints: str = cfg_cntx.get("remediation_endpoints", "")
        if not feature_endpoints:
            logger.error("Could not find the controller endpoints")
            raise ValueError("Could not find controller endpoints")
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
                        controller_obj=controller_obj,
                        logger=logger,
                        endpoint_context=cfg_cntx[
                            f"{remediation_endpoint}_remediation"
                        ],
                        payload=config[remediation_endpoint],
                        **controller_dict,
                    )
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
