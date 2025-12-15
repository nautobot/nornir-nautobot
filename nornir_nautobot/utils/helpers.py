"""A set of helper utilities."""

from __future__ import annotations

import errno
import importlib
import logging
import pathlib
import traceback
from base64 import b64encode
from typing import TYPE_CHECKING, Any

import jmespath
from jinja2 import BaseLoader, Environment, select_autoescape
from jinja2 import exceptions as jinja_errors

from nornir_nautobot.constants import ERROR_CODES

if TYPE_CHECKING:
    from logging import Logger


LOGGER = logging.getLogger(__name__)


def make_folder(folder):
    """Helper method to sanely create folders."""
    if not pathlib.Path(folder).exists():
        # Still try and except, since their may be race conditions.
        try:
            pathlib.Path(folder).mkdir(parents=True)
        except OSError as error:
            if error.errno != errno.EEXIST:
                raise


def snake_to_title_case(snake_string):
    """Convert snake_case into TitleCase."""
    return "".join(word.capitalize() for word in snake_string.lower().split("_"))


def import_string(dotted_path):
    """Import the python object by dotted_path string ."""
    module_name, class_name = dotted_path.rsplit(".", 1)
    try:
        return getattr(importlib.import_module(module_name), class_name)
    except (ModuleNotFoundError, AttributeError):
        return None


def get_stack_trace(exc: Exception) -> str:
    """Converts the provided exception's stack trace into a string."""
    stack_trace_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    return "".join(stack_trace_lines)


def is_truthy(arg):
    """Convert "truthy" strings into Booleans.

    Args:
        arg (str): Truthy string (True values are y, yes, t, true, on and 1; false values are n, no,
        f, false, off and 0. Raises ValueError if val is anything else.

    Examples:
        >>> is_truthy('yes')
        True
    """
    if isinstance(arg, bool):
        return arg

    val = str(arg).lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    if val in ("n", "no", "f", "false", "off", "0"):
        return False
    return True


def get_error_message(error_code: str, **kwargs: Any) -> str:
    """Get the error message for a given error code.

    Args:
        error_code (str): The error code.
        **kwargs: Any additional context data to be interpolated in the error message.

    Returns:
        str: The constructed error message.
    """
    try:
        error_message = ERROR_CODES.get(error_code, ERROR_CODES["E1XXX"]).error_message.format(**kwargs)
    except KeyError as missing_kwarg:
        error_message = f"Error Code was found, but failed to format, message expected kwarg `{missing_kwarg}`."
    except Exception:  # pylint: disable=broad-except
        error_message = "Error Code was found, but failed to format message, unknown cause."
    return f"{error_code}: {error_message}"


def render_jinja2(template_code: str, context: dict) -> str:
    """Render a Jinja2 template with the provided context.

    Returns a plain Python string (no Django SafeString).

    Args:
        template_code (str): The Jinja2 template code to render.
        context (dict): The context to render the template with.

    Returns:
        str: The rendered template as a plain Python string.
    """
    env = Environment(
        loader=BaseLoader(),
        autoescape=select_autoescape(
            disabled_extensions=(),
            default_for_string=False,
            default=False,
        ),
    )

    template = env.from_string(template_code)
    return template.render(**context)


def render_jinja_template(obj, logger: Logger, template: str) -> str:
    """Helper function to render Jinja templates.

    Args:
        obj (Device): The Device object from Nautobot.
        logger (Logger): Logger to log error messages to.
        template (str): A Jinja2 template to be rendered.

    Returns:
        str: The ``template`` rendered.

    Raises:
        ValueError: When there is an error rendering the ``template``.
    """
    try:
        return render_jinja2(template_code=template, context={"obj": obj})
    except jinja_errors.UndefinedError as error:
        error_msg = (
            "`E3019:` Jinja encountered and UndefinedError`, check the template "
            "for missing variable definitions.\n"
            f"Template:\n{template}\n"
            f"Original Error: {error}"
        )
        logger.error(error_msg, extra={"object": obj})
        raise ValueError(error_msg) from error

    except jinja_errors.TemplateSyntaxError as error:  # Also catches subclass of TemplateAssertionError
        error_msg = (
            f"`E3020:` Jinja encountered a SyntaxError at line number {error.lineno},"
            f"check the template for invalid Jinja syntax.\nTemplate:\n{template}\n"
            f"Original Error: {error}"
        )
        logger.error(error_msg, extra={"object": obj})
        raise ValueError(error_msg) from error
    # Intentionally not catching TemplateNotFound errors since template is passes as a string and not a filename
    except jinja_errors.TemplateError as error:  # Catches all remaining Jinja errors
        error_msg = (
            "`E3021:` Jinja encountered an unexpected TemplateError; check the template for correctness\n"
            f"Template:\n{template}\n"
            f"Original Error: {error}"
        )
        logger.error(error_msg, extra={"object": obj})
        raise ValueError(error_msg) from error


def base_64_encode_credentials(username: str, password: str) -> str:
    """Encode username and password into base64.

    Args:
        username (str): The username to encode.
        password (str): The password to encode.

    Returns:
        str: Base64 encoded credentials.

    Raises:
        ValueError: If username or password is not passed.
    """
    if not username or not password:
        exc_msg: str = "Username and/or password not passed, can't encode."
        raise ValueError(exc_msg)

    credentials_str: bytes = f"{username}:{password}".encode()
    return f"Basic {b64encode(s=credentials_str).decode(encoding='utf-8')}"


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

    Raises:
        ValueError: If base_url or endpoint is not passed.
    """
    if not base_url or not endpoint:
        exc_msg: str = "Base or endpoint not passed, can not properly format url."
        raise ValueError(exc_msg)

    base_url = base_url.removesuffix("/")

    endpoint = endpoint.removeprefix("/")

    return f"{base_url}/{endpoint}"


def add_api_path_to_url(api_path: str, base_url: str) -> str:
    """Add API path to base url.

    Args:
        api_path (str): API path, i.e. api/v1
        base_url (str): Controller base url.

    Returns:
        str: Base url with API path.
    """
    if api_path not in base_url:
        return format_base_url_with_endpoint(
            base_url=base_url,
            endpoint=api_path,
        )
    return base_url


def resolve_controller_url(
    obj,
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
        controller = controller_group.controller
        controller_url = controller.external_integration.remote_url
    elif controllers := obj.controllers.all():
        for cntrlr in controllers:
            if controller_type in cntrlr.platform.name.lower():
                controller_url = cntrlr.external_integration.remote_url
    if not controller_url:
        exc_msg: str = "Could not find the Controller API URL"
        logger.error(exc_msg)
        raise ValueError(exc_msg)
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
    logger: Logger,
) -> dict[Any, Any] | list[dict[str, Any]]:
    """Resolve jmespath.

    Args:
        jmespath_values (dict[str, str]): Jmespath dictionary.
        api_response (Any): API response.
        logger (Logger): Logger object.

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
    if not data_fields:
        logger.warning("No data fields resolved from jmespath")
        return data_fields
    lengths = [len(v) for v in data_fields.values() if isinstance(v, list)]
    if lengths == [1]:
        return data_fields
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
    api_endpoint = api_endpoint.removesuffix("/")
    api_endpoint = f"{api_endpoint}?{query.pop(0)}"
    if not query:
        return api_endpoint
    for q in query:
        api_endpoint = f"{api_endpoint}&{q}"
    return api_endpoint
