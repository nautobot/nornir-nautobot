"""Classes and functions for controller dispatcher utils."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Optional, Union

import requests
from requests import exceptions as req_exceptions
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

if TYPE_CHECKING:
    from logging import Logger


class ConnectionMixin:
    """Mixin to connect to a service."""

    @classmethod
    def configure_session(cls) -> requests.Session:
        """Configure a requests session.

        Returns:
            Session: Requests session.
        """
        session: requests.Session = requests.Session()
        retries = Retry(
            total=2,
            backoff_factor=0.5,
            backoff_max=5.0,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        session.mount(
            prefix="https://",
            adapter=HTTPAdapter(max_retries=retries),
        )
        return session

    @classmethod
    def _return_response(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        cls,
        method: str,
        url: str,
        headers: dict[str, str],
        session: requests.Session,
        logger: Logger,
        body: Optional[Union[dict[str, str], str]] = None,
        verify: bool = True,
    ) -> Optional[requests.Response]:
        """Create request for authentication and return response object.

        Args:
            method (str): HTTP Method to use.
            url (str): URL to send request to.
            headers (dict): Headers to use in request.
            session (Session): Session to use.
            logger (Logger): The dispatcher's logger.
            body (dict[str, str] | str | None): Body of request.
            verify (bool): Verify SSL certificate.

        Returns:
            Optional[Response]: API Response object.
        """
        if method in ["POST", "PUT"] and isinstance(body, dict):
            body = json.dumps(body)
        with session as ses:
            try:
                response: Optional[requests.Response] = ses.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=body,
                    timeout=(50.0, 100.0),
                    verify=verify,
                )
            except req_exceptions.SSLError as exc_ssl:
                logger.error(f"SSL error occurred: {exc_ssl}")
                response = None
            except req_exceptions.Timeout as exc_timeout:
                logger.error(f"Request timed out: {exc_timeout}")
                response = None
            except req_exceptions.ConnectionError as exc_conn:
                logger.error(f"Connection error occurred: {exc_conn}")
                response = None
            except req_exceptions.RequestException as exc_req:
                logger.error(f"Request exception occurred: {exc_req}")
                response = None
        if response is None:
            return response
        if not response.ok:
            logger.error(
                f"Endpoint {url} returned {response.status_code}: {response.text}",
            )
            return None
        return response

    @classmethod
    def return_response_obj(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        cls,
        method: str,
        url: str,
        headers: dict[str, str],
        session: requests.Session,
        logger: Logger,
        body: dict[str, str] | str | None = None,
        verify: bool = True,
    ) -> Optional[requests.Response]:
        """Create request for authentication and return response object.

        Args:
            method (str): HTTP Method to use.
            url (str): URL to send request to.
            headers (dict): Headers to use in request.
            session (Session): Session to use.
            logger (Logger): The dispatcher's logger.
            body (dict[str, str] | str | None): Body of request.
            verify (bool): Verify SSL certificate.

        Returns:
            Optional[Response]: API Response object or None.
        """
        return cls._return_response(
            method=method,
            url=url,
            headers=headers,
            session=session,
            logger=logger,
            body=body,
            verify=verify,
        )

    @classmethod
    def return_response_content(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        cls,
        method: str,
        url: str,
        headers: dict[str, str],
        session: requests.Session,
        logger: Logger,
        body: dict[str, str] | str | None = None,
        verify: bool = True,
    ) -> Any:
        """Create request and return response payload.

        Args:
            method (str): HTTP Method to use.
            url (str): URL to send request to.
            headers (dict): Headers to use in request.
            session (Session): Session to use.
            logger (Logger): The dispatcher's logger.
            body (dict[str, str] | str | None): Body of request.
            verify (bool): Verify SSL certificate.

        Returns:
            Any: API Response.
        """
        response: Optional[requests.Response] = None
        try:
            response = cls._return_response(
                method=method,
                url=url,
                headers=headers,
                session=session,
                logger=logger,
                body=body,
                verify=verify,
            )
            if not response:
                return response
            return response.json()
        except req_exceptions.JSONDecodeError:
            if not response:
                return response
            return response.text
        except req_exceptions.HTTPError as http_err:
            logger.error(http_err)
            return None
