"""A set of helper utilities."""

import errno
import importlib
import logging
import os
import re
import traceback
import unicodedata
from typing import Any

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


def command_to_filename(command, replacement="_"):
    """
    Convert a command string into a filesystem-safe filename.

    This function sanitizes a command string so it can safely be used as a filename by:
    1. Normalizing Unicode characters to their ASCII equivalents.
    2. Replacing the pipe symbol '|' (with or without surrounding spaces) with two replacement characters.
    3. Replacing characters that are illegal in most filesystems (e.g., / : * ? " < >) with the replacement character.
    4. Replacing all spaces with the replacement character.

    Args:
        command (str): The input command string to sanitize.
        replacement (str): The character to use as a substitute for illegal or special characters. Default is underscore ('_').

    Returns:
        str: A sanitized, ASCII-only, filesystem-safe version of the command string suitable for use as a filename.
    """
    # 1. Normalize Unicode characters (e.g., accented characters to ASCII equivalents)
    #    and then ignore non-ASCII. This handles many international characters.
    command_file_name = unicodedata.normalize("NFKD", command).encode("ascii", "ignore").decode("ascii")

    # 2. Replace the '|' with the replacement character
    command_file_name = re.sub(r"\s*\|\s*", 2 * replacement, command_file_name)

    # 3. Replace characters illegal in most filesystems with the replacement character
    #    Common illegal characters: / \ : * ? " < > |
    #    Also replace leading/trailing whitespace, and control characters.
    #    This regex targets common illegal filename characters and also handles multiple
    #    replacement characters in a row (e.g., 'foo///bar' becomes 'foo_bar').
    command_file_name = re.sub(r"\s*[\/\\:*?\"<>]\s*", replacement, command_file_name)

    # 4. Replace spaces with the replacement character
    command_file_name = re.sub(r"\s+", replacement, command_file_name).strip(replacement)

    return command_file_name
