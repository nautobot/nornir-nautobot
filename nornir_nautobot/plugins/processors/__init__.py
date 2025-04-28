"""BaseProcessor for the nornir."""

import logging

from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task

LOGGER = logging.getLogger(__name__)


class BaseProcessor:
    """Base Processor for nornir."""

    task_name = "'no task defined'"

    def task_started(self, task: Task) -> None:
        """Boilerplate Nornir processor for task_started."""

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """Boilerplate Nornir processor for task_completed."""

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Boilerplate Nornir processor for task_instance_started."""

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Boilerplate Nornir processor for task_instance_completed."""

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Boilerplate Nornir processor for subtask_instance_started."""

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Boilerplate Nornir processor for subtask_instance_completed."""


class BaseLoggingProcessor(BaseProcessor):
    """Base Processor with logging for nornir."""

    def task_started(self, task: Task) -> None:
        """Boilerplate Nornir processor for task_started with logging."""
        LOGGER.info("%s | Task started", task.name)

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """Boilerplate Nornir processor for task_completed with logging."""
        LOGGER.info("%s | Task task_completed", task.name)

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Boilerplate Nornir processor for task_instance_started with logging."""
        LOGGER.info("%s | Task instance %s has started", host.name, task.name)

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Boilerplate Nornir processor for task_instance_completed with logging."""
        LOGGER.info("%s | Task instance %s has completed", host.name, task.name)

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Boilerplate Nornir processor for subtask_instance_started with logging."""
        LOGGER.info("%s | Task instance subtask %s has started.", task.host.name, task.name)

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Boilerplate Nornir processor for subtask_instance_completed with logging."""
        LOGGER.info("%s | Task instance subtask %s has completed.", task.host.name, task.name)
