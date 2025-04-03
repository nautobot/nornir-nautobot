import os
import sys
import traceback

from typing import Any, Optional, Dict, Callable

from nornir.core.task import Result, Task

from jinja2 import Environment, FileSystemLoader, StrictUndefined

FiltersDict = Optional[Dict[str, Callable[..., str]]]


def template_file(
    task: Task,
    template: str,
    path: str,
    jinja_filters: Optional[FiltersDict] = None,
    jinja_env: Optional[Environment] = None,
    obj=None,
    logger=None,
    **kwargs: Any
) -> Result:
    """
    Renders contants of a file with jinja2. All the host data is available in the template

    Arguments:
        template: filename
        path: path to dir with templates
        jinja_filters: jinja filters to enable. Defaults to nornir.config.jinja2.filters
        jinja_env: A fully configured jinja2 environment
        **kwargs: additional data to pass to the template

    Returns:
        Result object with the following attributes set:
          * result (``string``): rendered string
    """
    jinja_filters = jinja_filters or {}
    path = os.path.abspath(path)

    if jinja_env:
        env = jinja_env
        env.loader = FileSystemLoader(path)
    else:
        env = Environment(
            loader=FileSystemLoader(path), undefined=StrictUndefined, trim_blocks=True,
        )
    env.filters.update(jinja_filters)
    
    try:
        jinja_template = env.get_template(template)
        text = jinja_template.render(host=task.host, **kwargs)
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
        if filename != "unknown" and line_number != "unknown":
            try:
                with open(os.path.join(path, template), "r") as f:
                    template_content = f.readlines()
                if 0 < int(line_number) <= len(template_content):
                    template_line = template_content[int(line_number) - 1].strip()
            except (IOError, ValueError) as e:
                template_line = f"Failed to read template: {str(e)}"

        error_msg = f"Error rendering template '{template}' at {filename}:{line_number}\nLine: {template_line}\nError Type: {error_type}\nMessage: {message}"
        logger.error(error_msg, extra={"object": obj})
        raise