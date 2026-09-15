"""BaseProcessor for the nornir."""

import logging
import traceback
from typing import Optional, Set

from nornir.core.exceptions import NornirSubTaskError
from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task

LOGGER = logging.getLogger(__name__)


def _clear_exception_frames(exception: Optional[BaseException], seen: Set[int]) -> None:
    """Recursively drop the frame locals held by `exception` and every exception it chains to.

    Follows `__cause__`, `__context__`, and the sub-results stored on a `NornirSubTaskError`.
    `seen` holds the `id()` of every exception already visited, so a cyclic chain terminates.

    Args:
        exception (Optional[BaseException]): Exception to clear, or `None`.
        seen (Set[int]): Identities of the exceptions already visited by this walk.
    """
    while exception is not None and id(exception) not in seen:
        seen.add(id(exception))
        traceback.clear_frames(exception.__traceback__)
        _clear_exception_frames(exception.__cause__, seen)

        if isinstance(exception, NornirSubTaskError):
            # Typed as a single Result, but nornir raises it with a MultiResult in practice.
            sub_results = exception.result if isinstance(exception.result, list) else [exception.result]
            for sub_result in sub_results:
                _clear_exception_frames(sub_result.exception, seen)

        exception = exception.__context__


def clear_result_exception_frames(result: MultiResult) -> None:
    """Release the frame locals pinned by any exception stored in `result`.

    Nornir keeps the live exception object on every failed `Result`, and those results stay in the
    `AggregatedResult` until the play ends. The traceback therefore pins the connection frames of
    the underlying driver for the whole run, including any file descriptors their locals hold. Only
    frame locals are dropped; the formatted traceback string nornir has already written to
    `Result.result`, and the exception message, are unaffected.

    Processors that override `task_instance_completed` without calling `super()` should call this
    directly.

    Args:
        result (MultiResult): Nornir MultiResult for a completed task instance.
    """
    for task_result in result:
        _clear_exception_frames(task_result.exception, set())


class BaseProcessor:
    """Base Processor for nornir."""

    task_name = "'no task defined'"

    def task_started(self, task: Task) -> None:
        """Boilerplate Nornir processor for task_started."""

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """Boilerplate Nornir processor for task_completed."""

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Boilerplate Nornir processor for task_instance_started."""

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:  # pylint: disable=unused-argument
        """Updated task_instance_completed, releasing stored exception frames."""
        clear_result_exception_frames(result)

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
        super().task_instance_completed(task, host, result)

    def subtask_instance_started(self, task: Task, host: Host) -> None:
        """Boilerplate Nornir processor for subtask_instance_started with logging."""
        LOGGER.info("%s | Task instance subtask %s has started.", task.host.name, task.name)

    def subtask_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:
        """Boilerplate Nornir processor for subtask_instance_completed with logging."""
        LOGGER.info("%s | Task instance subtask %s has completed.", task.host.name, task.name)
