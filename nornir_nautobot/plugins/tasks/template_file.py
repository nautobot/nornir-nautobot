"""This is a vendored and updated implementation of the template_file task from nornor-jinja2."""

import logging
import os
import sys
import traceback
from typing import Any, Callable, Dict, Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from nornir.core.task import Result, Task

from nornir_nautobot.utils.helpers import get_error_message

FiltersDict = Optional[Dict[str, Callable[..., str]]]
LOGGER = logging.getLogger(__name__)


def template_file(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-branches,too-many-statements
    task: Task,
    template: str,
    path: str,
    jinja_filters: Optional[FiltersDict] = None,
    jinja_env: Optional[Environment] = None,
    obj=None,
    logger=None,
    **kwargs: Any,
) -> Result:
    """
    Renders contents of a file with jinja2. All the host data is available in the template.

    Arguments:
        task: Nornir task object
        template: filename
        path: path to dir with templates
        jinja_filters: jinja filters to enable. Defaults to nornir.config.jinja2.filters
        jinja_env: A fully configured jinja2 environment
        obj: An object to pass to the template context
        logger: Logger to use for logging errors
        **kwargs: additional data to pass to the template

    Returns:
        Result object with the following attributes set:
          * result (``string``): rendered string
    """
    jinja_filters = jinja_filters or {}
    path = os.path.abspath(path)
    if not logger:
        logger = LOGGER

    if jinja_env:
        env = jinja_env
        env.loader = FileSystemLoader(path)
    else:
        env = Environment(  # noqa: S701
            loader=FileSystemLoader(path),
            undefined=StrictUndefined,
            trim_blocks=True,
        )
    env.filters.update(jinja_filters)

    try:
        jinja_template = env.get_template(template)
        text = jinja_template.render(host=task.host, obj=obj, **kwargs)
        return Result(host=task.host, result=text)
    except Exception as error:
        error_type = type(error).__name__
        message = str(error)

        # Prefer e.filename and e.lineno if available
        filename = getattr(error, "filename", None)
        line_number = getattr(error, "lineno", None)

        # Fall back to traceback parsing if attributes are missing or invalid
        if not filename or not line_number:
            _, _, exc_traceback = sys.exc_info()
            tb_list = traceback.extract_tb(exc_traceback)
            for frame in reversed(tb_list):  # Start from the end (most specific frame)
                if path in frame.filename or frame.filename.startswith("<"):
                    filename = frame.filename
                    line_number = frame.lineno
                    break
            # If still not found, use defaults
            filename = filename or "unknown"
            line_number = line_number or "unknown"

        # Always extract the original line from the template
        template_line = "Not available"
        template_line_context = "Not available"
        if filename != "unknown" and line_number != "unknown":
            try:
                with open(os.path.join(path, filename), "r", encoding="utf8") as f:
                    template_content = f.readlines()
                if 0 < int(line_number) <= len(template_content):
                    template_line = template_content[int(line_number) - 1].strip()
                    start = max(0, int(line_number) - 3)
                    end = min(len(template_content), int(line_number) + 2)
                    template_line_context = "".join(template_content[start:end]).strip()
            except (IOError, ValueError) as e:
                template_line = f"Failed to read template: {str(e)}"

        error_id = ""
        if error_type == "UndefinedError":
            error_id = "E1010"
        elif error_type == "TemplateSyntaxError":
            error_id = "E1011"
            template_line = template_line_context
        elif error_type == "TemplateNotFound":
            error_id = "E1012"
        elif error_type == "TemplateError":
            error_id = "E1013"
        elif error_type == "TemplateAssertionError":
            error_id = "E1034"
        if error_id:
            error_msg = get_error_message(
                error_id,
                template=template,
                filename=filename,
                line_number=line_number,
                template_line=template_line,
                error_type=error_type,
                message=message,
            )
            logger.error(error_msg, extra={"object": obj})
            raise

        error_msg = f"Error rendering template '{template}' at {filename}:{line_number}\nLine: {template_line}\nError Type: {error_type}\nMessage: {message}"
        logger.error(error_msg, extra={"object": obj})
        raise
