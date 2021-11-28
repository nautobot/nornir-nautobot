"""Provide logging facility for Nautobot/Python usage."""

import logging


class NornirLogger:
    """Similar to a mixin, to utilize Python logging and Jobs Result obj."""

    def __init__(self, name, nautobot_job=None, debug=False, job_result=None):
        """Initialize the object."""
        self.job_result = job_result or nautobot_job
        self.logger = logging.getLogger(name)
        self.debug = debug
        self.nautobot_job = nautobot_job or job_result
        if job_result is not None:
            log_message = (
                "The arg named `job_result` has been renamed to `nautobot_job`; please update to use this name."
            )
            self.logger.warning(log_message)
            job_result.log_warning(log_message)

    def log_debug(self, message):
        """Debug, does not take obj, and only logs to jobs result when in global debug mode."""
        if self.nautobot_job and self.debug:
            self.nautobot_job.log_debug(message)
        self.logger.debug(message)

    def log_info(self, obj, message):
        """Log to Python logger and jogs results for info messages."""
        if self.nautobot_job:
            self.nautobot_job.log_info(obj, message)
        self.logger.info("%s | %s", str(obj), message)

    def log_success(self, obj, message):
        """Log to Python logger and jogs results for success messages."""
        if self.nautobot_job:
            self.nautobot_job.log_success(obj, message)
        self.logger.info("%s | %s", str(obj), message)

    def log_warning(self, obj, message):
        """Log to Python logger and jogs results for warning messages."""
        if self.nautobot_job:
            self.nautobot_job.log_warning(obj, message)
        self.logger.warning("%s | %s", str(obj), message)

    def log_failure(self, obj, message):
        """Log to Python logger and jogs results for failure messages."""
        if self.nautobot_job:
            self.nautobot_job.log_failure(obj, message)
        self.logger.error("%s | %s", str(obj), message)
