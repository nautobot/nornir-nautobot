"""Provide logging facility for Nautobot/Python usage."""

import logging


class NornirLogger:
    """Similar to a mixin, to utilize Python logging and Jobs Result obj."""

    def __init__(self, name, job_result=None, debug=False):
        """Initialize the object."""
        self.job_result = job_result
        self.logger = logging.getLogger(name)
        self.debug = debug

    def log_debug(self, message):
        """Debug, does not take obj, and only logs to jobs result when in global debug mode."""
        if self.job_result and self.debug:
            self.job_result.log_debug(message)
        self.logger.debug(message)

    def log_info(self, obj, message):
        """Log to Python logger and jogs results for info messages."""
        if self.job_result:
            self.job_result.log_info(obj, message)
        self.logger.info("%s | %s", str(obj), message)

    def log_success(self, obj, message):
        """Log to Python logger and jogs results for success messages."""
        if self.job_result:
            self.job_result.log_success(obj, message)
        self.logger.info("%s | %s", str(obj), message)

    def log_warning(self, obj, message):
        """Log to Python logger and jogs results for warning messages."""
        if self.job_result:
            self.job_result.log_warning(obj, message)
        self.logger.warning("%s | %s", str(obj), message)

    def log_failure(self, obj, message):
        """Log to Python logger and jogs results for failure messages."""
        if self.job_result:
            self.job_result.log_failure(obj, message)
        self.logger.error("%s | %s", str(obj), message)
