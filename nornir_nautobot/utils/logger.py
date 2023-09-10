"""Provide logging facility for Nautobot/Python usage."""

import logging

from typing import Any


class NornirLogger:
    """Similar to a mixin, to utilize Python logging and Jobs Result obj."""

    def __init__(self, name: str, nautobot_job=None, debug: bool = False, job_result=None):
        """Initialize the object."""
        self.job_result = job_result or nautobot_job
        self.logger = logging.getLogger(name)
        self.debug = debug
        self.nautobot_job = nautobot_job or job_result

    def log_debug(self, message: str, extra: Any=None):
        """Debug, does not take obj, and only logs to jobs result when in global debug mode."""
        if self.nautobot_job and self.debug:
            self.nautobot_job.logging.debug(message, extra=extra)
        self.logger.debug(message)

    def log_info(self, message: str, extra: Any=None):
        """Log to Python logger and jogs results for info messages."""
        if self.nautobot_job:
            self.nautobot_job.logging.info(message, extra=extra)
        self.logger.info("%s | %s", str(extra), message)

    def log_warning(self, message: str, extra: Any=None):
        """Log to Python logger and jogs results for warning messages."""
        if self.nautobot_job:
            self.nautobot_job.logging.warning(message, extra=extra)
        self.logger.warning("%s | %s", str(extra), message)

    def log_error(self, message: str, extra: Any=None):
        """Log to Python logger and jogs results for error messages."""
        if self.nautobot_job:
            self.nautobot_job.logging.error(message, extra=extra)
        self.logger.error("%s | %s", str(extra), message)

    def log_critical(self, message: str, extra: Any=None):
        """Log to Python logger and jogs results for critical messages."""
        if self.nautobot_job:
            self.nautobot_job.logging.critical(message, extra=extra)
        self.logger.critical("%s | %s", str(extra), message)