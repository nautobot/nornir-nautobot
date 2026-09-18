"""BaseProcessor for the nornir."""

import gc
import logging
import os
import resource
import threading
import traceback
from typing import Optional, Set

from nornir.core.exceptions import NornirSubTaskError
from nornir.core.inventory import Host
from nornir.core.task import AggregatedResult, MultiResult, Task

LOGGER = logging.getLogger(__name__)

#: `select()` cannot wait on a descriptor numbered at or above `FD_SETSIZE`, so drivers that use it
#: fail once descriptor numbers reach this value even when `RLIMIT_NOFILE` is higher.
SELECT_FD_SETSIZE = 1024


def open_fd_count() -> Optional[int]:
    """Count the descriptors this process has open, or return None if the platform cannot say.

    Returns:
        Optional[int]: Number of open descriptors, or `None` on platforms without `/proc` or `/dev/fd`.
    """
    for fd_dir in ("/proc/self/fd", "/dev/fd"):
        try:
            return len(os.listdir(fd_dir))
        except OSError:
            continue
    return None


def fd_ceiling() -> Optional[int]:
    """Return the usable descriptor ceiling for this process, or None if it cannot be determined.

    Capped at `SELECT_FD_SETSIZE` because a higher `RLIMIT_NOFILE` is not actually reachable by a
    driver whose event loop uses `select()`.

    Returns:
        Optional[int]: Effective descriptor ceiling, or `None` if `RLIMIT_NOFILE` is unavailable.
    """
    try:
        soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    except (OSError, ValueError):  # pragma: no cover - platform dependent
        return None
    if soft in (resource.RLIM_INFINITY, -1):
        return SELECT_FD_SETSIZE
    return min(soft, SELECT_FD_SETSIZE)


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

    #: Collect once open descriptors reach this fraction of the usable ceiling, or 0 to disable.
    gc_fd_high_water = 0.7

    #: Task instances to wait before testing again after a collection fails to free descriptors.
    #: Without this, a play whose descriptors are legitimately in use would collect on every task.
    gc_cooldown = 50

    #: Optional fixed-interval collection, for platforms that cannot report a descriptor count.
    #: 0 leaves the descriptor-driven check above as the only trigger.
    gc_collect_interval = 0

    _completed_count = 0
    _cooldown_until = 0
    _gc_lock = threading.Lock()

    def _collect_if_due(self) -> None:
        """Run a full garbage collection if descriptor pressure, or the fixed interval, calls for it.

        Held under a lock so that concurrent task instances cannot trigger overlapping collections.
        """
        with BaseProcessor._gc_lock:
            BaseProcessor._completed_count += 1
            completed = BaseProcessor._completed_count
            if completed < BaseProcessor._cooldown_until:
                return

            if self.gc_collect_interval and completed % self.gc_collect_interval == 0:
                gc.collect()
                return

            if not self.gc_fd_high_water:
                return
            ceiling = fd_ceiling()
            open_fds = open_fd_count()
            if ceiling is None or open_fds is None:
                return
            high_water = ceiling * self.gc_fd_high_water
            if open_fds < high_water:
                return

            # A full collection: these cycles reach the oldest generation, which a generation 0
            # pass would not free.
            gc.collect()

            remaining = open_fd_count()
            if remaining is not None and remaining >= high_water:
                # The descriptors are in use rather than collectable, so collecting again will not
                # help. Back off instead of collecting after every subsequent task instance.
                BaseProcessor._cooldown_until = completed + self.gc_cooldown

    def task_started(self, task: Task) -> None:
        """Boilerplate Nornir processor for task_started."""

    def task_completed(self, task: Task, result: AggregatedResult) -> None:
        """Boilerplate Nornir processor for task_completed."""

    def task_instance_started(self, task: Task, host: Host) -> None:
        """Boilerplate Nornir processor for task_instance_started."""

    def task_instance_completed(self, task: Task, host: Host, result: MultiResult) -> None:  # pylint: disable=unused-argument
        """Updated task_instance_completed, releasing stored exception frames."""
        clear_result_exception_frames(result)
        self._collect_if_due()

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
