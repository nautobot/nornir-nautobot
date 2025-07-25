"""Classes and functions for controller dispatcher utils."""

from logging import Logger
from typing import Any, Optional, Union

import jmespath
from nautobot.apps.choices import (
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
)
from nautobot.dcim.models import Controller, Device
from nautobot.extras.models import SecretsGroup, SecretsGroupAssociation
from requests import Response, Session
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError, JSONDecodeError
from urllib3.util import Retry


def format_base_url_with_endpoint(
    base_url: str,
    endpoint: str,
) -> str:
    """Format base url with API endpoint.

    Args:
        base_url (str): Base url to format.
        endpoint (str): Endpoint to format with.

    Returns:
        str: Formatted url.
    """
    if not base_url or not endpoint:
        raise ValueError("Base or endpoint not passed, can not properly format url.")

    if base_url.endswith("/"):
        base_url = base_url[:-1]

    if endpoint.startswith("/"):
        endpoint = endpoint[1:]

    return f"{base_url}/{endpoint}"


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


def resolve_controller_url(
    obj: Device,
    controller_type: str,
    logger: Logger,
) -> str:
    """Resolve controller url.

    Args:
        obj (Device): Device object.
        controller_type (str): Name of the controller type.
        logger (Logger): Logger object.

    Returns:
        str: Controller url

    Raises:
        ValueError: Could not find the controller API URL from external integration.
    """
    controller_url: str = ""
    if controller_group := obj.controller_managed_device_group:
        controller: Controller = controller_group.controller
        controller_url = controller.external_integration.remote_url
    elif controllers := obj.controllers.all():
        for cntrlr in controllers:
            if controller_type in cntrlr.platform.name.lower():
                controller_url = cntrlr.external_integration.remote_url
    if not controller_url:
        logger.error("Could not find the Meraki Dashboard API URL")
        raise ValueError("Could not find the Meraki Dashboard API URL")
    return controller_url


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
    if not parameters or not param_mapper:
        return params
    for param in parameters:
        if param.lower() not in [p.lower() for p in param_mapper]:
            continue
        for k, v in param_mapper.items():
            if k.lower() == param.lower():
                params.update({k: v})
    return params


def resolve_jmespath(
    jmespath_values: dict[str, str],
    api_response: Any,
) -> dict[Any, Any] | list[dict[str, Any]]:
    """Resolve jmespath.

    Args:
        jmespath_values (dict[str, str]): Jmespath list.
        api_response (Any): API response.

    Returns:
        dict[Any, Any] | list[dict[str, Any]]: Resolved jmespath data fields.
    """
    data_fields: dict[str, Any] = {}

    for key, value in jmespath_values.items():
        j_value: Any = jmespath.search(
            expression=value,
            data=api_response,
        )
        if j_value:
            data_fields.update({key: j_value})
    lengths = [len(v) for v in data_fields.values() if isinstance(v, list)]
    if len(lengths) != len(data_fields.values()):
        return data_fields
    if len(set(lengths)) != 1:
        return data_fields
    keys = list(data_fields.keys())
    values = zip(*data_fields.values())
    return [dict(zip(keys, v)) for v in values]


def resolve_query(api_endpoint: str, query: list[str]) -> str:
    """Append query to api endpoint.

    Args:
        api_endpoint (str): API endpoint URL.
        query (list[str]): Query list.

    Returns:
        str: API endpoint with query appended.
    """
    if api_endpoint.endswith("/"):
        api_endpoint = api_endpoint[:-1]
    api_endpoint = f"{api_endpoint}?{query.pop(0)}"
    if not query:
        return api_endpoint
    for q in query:
        api_endpoint = f"{api_endpoint}&{q}"
    return api_endpoint


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
    def _return_response(
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

    @classmethod
    def return_response_obj(
        cls,
        method: str,
        url: str,
        headers: dict[str, str],
        session: Session,
        logger: Logger,
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
        return cls._return_response(
            method=method,
            url=url,
            headers=headers,
            session=session,
            body=body,
            verify=verify,
        )

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
            response: Response = cls._return_response(
                method=method,
                url=url,
                headers=headers,
                session=session,
                body=body,
                verify=verify,
            )
            json_response: dict[str, Any] = response.json()
            return json_response
        except JSONDecodeError:
            text_response: str = response.text
            return text_response
        except HTTPError as http_err:
            logger.error(http_err)
            return
