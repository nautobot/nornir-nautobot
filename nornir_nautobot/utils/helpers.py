"""A set of helper utilities."""

from typing import Any

import errno
import os
import logging
import importlib
import traceback

from nornir_nautobot.constants import ERROR_CODES


LOGGER = logging.getLogger(__name__)


def make_folder(folder):
    """Helper method to sanely create folders."""
    if not os.path.exists(folder):
        # Still try and except, since their may be race conditions.
        try:
            os.makedirs(folder)
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
