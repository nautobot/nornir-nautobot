"""A set of helper utilities."""

import errno
import os
import logging
import importlib

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
