"""Base nornir dispatcher for controllers."""

import json
from abc import ABC, abstractmethod
from logging import Logger
from typing import Any, Optional, OrderedDict

import jmespath
from nautobot.apps.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.dcim.models import Device
from nautobot.extras.models import SecretsGroup, SecretsGroupAssociation
from nornir.core.task import Result, Task
from nornir_nautobot.plugins.tasks.dispatcher.default import NetmikoDefault


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
            data_fields.update({key: j_value})
    return data_fields


class BaseControllerDriver(NetmikoDefault, ABC):
    """Base Controller Dispatcher class."""

    @classmethod
    def _feature_name_parser(cls, feature_name: str) -> str:
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
        return feat

    @classmethod
    @abstractmethod
    def authenticate(
        cls,
        logger: Logger,
        obj: Device,
    ) -> Any:
        """Authenticate to controller.

        Args:
            logger (Logger): Logger object.
            obj (Device): Device object.

        Raises:
            ValueError: Could not find the controller API URL in config context.

        Returns:
            Any: Controller object.
        """
        pass

    @classmethod
    @abstractmethod
    def controller_setup(
        cls,
        controller_obj: Any,
        logger: Logger,
    ) -> dict[str, str]:
        """Setup for controller.

        Args:
            controller_obj (Any): The controller object, i.e DashboardAPI for controller.
            logger (Logger): Logger object.

        Returns:
            dict[str, str]: Map for controller data.
        """
        pass

    @classmethod
    @abstractmethod
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
        )
        controller_dict: dict[str, str] = cls.controller_setup(
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
            feature_name: str = cls._feature_name_parser(feature_name=feature)
            _running_config.update(
                {
                    feature_name: cls.resolve_endpoint(
                        controller_obj=controller_obj,
                        logger=logger,
                        endpoint_context=endpoints,
                        **controller_dict,
                    )
                }
            )
        processed_config: str = cls._process_config(
            logger=logger,
            running_config=json.dumps(obj=_running_config, indent=4),
            remove_lines=remove_lines,
            substitute_lines=substitute_lines,
            backup_file=backup_file,
        )
        return Result(host=task.host, result={"config": processed_config})
