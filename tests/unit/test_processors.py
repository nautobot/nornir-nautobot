"""Pytest for exception frame clearing in the base processors."""

import gc
import logging
import os
import threading
import traceback
import weakref
from unittest.mock import MagicMock

import pytest
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import MultiResult, Result

from nornir_nautobot.plugins.processors import (
    SELECT_FD_SETSIZE,
    BaseLoggingProcessor,
    BaseProcessor,
    clear_result_exception_frames,
    fd_ceiling,
    open_fd_count,
)


class Sentinel:
    """Plain object used to detect whether a frame local has been released."""


def _raise_holding(sentinel):
    """Raise an exception from a frame whose locals hold `sentinel`."""
    pinned = sentinel  # noqa: F841 - deliberately pinned in this frame's locals
    raise RuntimeError("boom")


def _pinning_exception():
    """Return an exception whose traceback frames are the only reference to a sentinel.

    Returns a `(exception, sentinel_ref)` tuple. `sentinel_ref` resolves to `None` once the
    traceback frames holding the sentinel have been cleared and collected.
    """
    sentinel = Sentinel()
    sentinel_ref = weakref.ref(sentinel)
    try:
        _raise_holding(sentinel)
    except RuntimeError as error:
        exception = error
    del sentinel
    return exception, sentinel_ref


def _pinning_exception_with_cause():
    """Return an exception that pins a sentinel through its `__cause__`."""
    cause, sentinel_ref = _pinning_exception()
    try:
        raise ValueError("wrapper") from cause
    except ValueError as error:
        return error, sentinel_ref


def _pinning_exception_with_context():
    """Return an exception that pins a sentinel through its implicit `__context__`."""
    context, sentinel_ref = _pinning_exception()
    try:
        raise context
    except RuntimeError:
        try:
            raise ValueError("wrapper")
        except ValueError as error:
            return error, sentinel_ref


def _pinning_subtask_error():
    """Return a `NornirSubTaskError` that pins a sentinel through its stored sub-results."""
    exception, sentinel_ref = _pinning_exception()
    return NornirSubTaskError(task=MagicMock(), result=_multi_result(_result_for(exception))), sentinel_ref


def _result_for(exception):
    """Build a nornir `Result` holding `exception` the way `Task.run` does."""
    return Result(
        MagicMock(),
        exception=exception,
        result="".join(traceback.format_exception(type(exception), exception, exception.__traceback__)),
        failed=True,
    )


def _multi_result(*results):
    """Build a `MultiResult` containing `results`."""
    multi_result = MultiResult("test_task")
    multi_result.extend(results)
    return multi_result


def _run_processor(processor, result):
    """Invoke `task_instance_completed` with throwaway task and host mocks."""
    task = MagicMock()
    task.name = "test_task"
    host = MagicMock()
    host.name = "test_host"
    processor.task_instance_completed(task, host, result)


def _is_released(sentinel_ref):
    """Return whether the weakly referenced sentinel has been collected."""
    gc.collect()
    return sentinel_ref() is None


def test_sentinel_is_pinned_without_clearing():
    """Guard the other tests: an untouched exception really does pin its frame locals."""
    _exception, sentinel_ref = _pinning_exception()

    assert not _is_released(sentinel_ref)


def test_direct_exception_frames_are_released():
    exception, sentinel_ref = _pinning_exception()
    result = _multi_result(_result_for(exception))

    _run_processor(BaseLoggingProcessor(), result)

    assert _is_released(sentinel_ref)


def test_cause_chain_frames_are_released():
    exception, sentinel_ref = _pinning_exception_with_cause()
    result = _multi_result(_result_for(exception))

    _run_processor(BaseLoggingProcessor(), result)

    assert _is_released(sentinel_ref)


def test_context_chain_frames_are_released():
    exception, sentinel_ref = _pinning_exception_with_context()
    result = _multi_result(_result_for(exception))

    _run_processor(BaseLoggingProcessor(), result)

    assert _is_released(sentinel_ref)


def test_subtask_error_result_frames_are_released():
    exception, sentinel_ref = _pinning_subtask_error()
    result = _multi_result(_result_for(exception))

    _run_processor(BaseLoggingProcessor(), result)

    assert _is_released(sentinel_ref)


def test_cyclic_context_chain_terminates():
    first, first_ref = _pinning_exception()
    second, second_ref = _pinning_exception()
    first.__context__ = second
    second.__context__ = first
    result = _multi_result(_result_for(first))

    _run_processor(BaseLoggingProcessor(), result)

    assert _is_released(first_ref)
    assert _is_released(second_ref)


def test_every_result_in_the_multi_result_is_cleared():
    first, first_ref = _pinning_exception()
    second, second_ref = _pinning_exception()
    result = _multi_result(_result_for(first), _result_for(second))

    _run_processor(BaseLoggingProcessor(), result)

    assert _is_released(first_ref)
    assert _is_released(second_ref)


def test_result_without_exception_is_a_noop():
    result = _multi_result(Result(MagicMock(), result="all good", failed=False))

    _run_processor(BaseLoggingProcessor(), result)


def test_empty_multi_result_is_a_noop():
    _run_processor(BaseLoggingProcessor(), _multi_result())


def test_traceback_text_and_message_are_preserved():
    exception, _sentinel_ref = _pinning_exception()
    result = _multi_result(_result_for(exception))
    expected_text = result[0].result

    _run_processor(BaseLoggingProcessor(), result)

    assert result[0].result == expected_text
    assert "RuntimeError: boom" in expected_text
    assert str(result[0].exception) == "boom"


def test_base_processor_releases_frames():
    exception, sentinel_ref = _pinning_exception()
    result = _multi_result(_result_for(exception))

    _run_processor(BaseProcessor(), result)

    assert _is_released(sentinel_ref)


def test_helper_is_usable_directly():
    exception, sentinel_ref = _pinning_exception()
    result = _multi_result(_result_for(exception))

    clear_result_exception_frames(result)

    assert _is_released(sentinel_ref)


def test_logging_processor_still_logs_completion(caplog):
    exception, _sentinel_ref = _pinning_exception()
    result = _multi_result(_result_for(exception))

    with caplog.at_level(logging.INFO, logger="nornir_nautobot.plugins.processors"):
        _run_processor(BaseLoggingProcessor(), result)

    assert "test_host | Task instance test_task has completed" in caplog.text


@pytest.mark.parametrize("processor_class", [BaseProcessor, BaseLoggingProcessor])
def test_clearing_is_stateless_across_calls(processor_class):
    processor = processor_class()
    for _ in range(2):
        exception, sentinel_ref = _pinning_exception()
        _run_processor(processor, _multi_result(_result_for(exception)))
        assert _is_released(sentinel_ref)


def _passing_result():
    """A MultiResult with no stored exception, as a successful task instance produces."""
    return _multi_result(Result(MagicMock(), result="config text", failed=False))


def _reset_gc_state():
    """Zero the process-wide collection state so the interval tests are independent."""
    with BaseProcessor._gc_lock:  # pylint: disable=protected-access
        BaseProcessor._completed_count = 0  # pylint: disable=protected-access
        BaseProcessor._cooldown_until = 0  # pylint: disable=protected-access


@pytest.fixture(name="collect_calls")
def _collect_calls(monkeypatch):
    """Record gc.collect() calls made by the processor, without actually collecting."""
    _reset_gc_state()
    calls = []
    monkeypatch.setattr("nornir_nautobot.plugins.processors.gc.collect", lambda: calls.append(1))
    return calls


@pytest.mark.parametrize("processor_class", [BaseProcessor, BaseLoggingProcessor])
def test_no_collection_while_descriptors_are_low(processor_class, collect_calls, monkeypatch):
    """A play whose driver leaks nothing must never pay for a collection."""
    monkeypatch.setattr("nornir_nautobot.plugins.processors.open_fd_count", lambda: 100)
    monkeypatch.setattr("nornir_nautobot.plugins.processors.fd_ceiling", lambda: 1000)

    processor = processor_class()
    for _ in range(500):
        _run_processor(processor, _passing_result())

    assert collect_calls == []


def test_collection_when_descriptors_pass_the_high_water_mark(collect_calls, monkeypatch):
    freed = {"done": False}
    monkeypatch.setattr("nornir_nautobot.plugins.processors.fd_ceiling", lambda: 1000)
    monkeypatch.setattr(
        "nornir_nautobot.plugins.processors.open_fd_count",
        lambda: 100 if freed["done"] else 800,
    )
    monkeypatch.setattr(
        "nornir_nautobot.plugins.processors.gc.collect",
        lambda: (collect_calls.append(1), freed.__setitem__("done", True)),
    )

    _run_processor(BaseProcessor(), _passing_result())
    assert len(collect_calls) == 1


def test_cooldown_when_collection_does_not_free_descriptors(collect_calls, monkeypatch):
    """Descriptors that are genuinely in use must not trigger a collection on every task."""
    monkeypatch.setattr("nornir_nautobot.plugins.processors.fd_ceiling", lambda: 1000)
    monkeypatch.setattr("nornir_nautobot.plugins.processors.open_fd_count", lambda: 900)
    monkeypatch.setattr(BaseProcessor, "gc_cooldown", 50, raising=False)

    processor = BaseProcessor()
    for _ in range(120):
        _run_processor(processor, _passing_result())

    # One collection at the first task, then a 50-task cooldown before each further attempt.
    assert len(collect_calls) == 3


def test_descriptor_check_can_be_disabled(collect_calls, monkeypatch):
    monkeypatch.setattr("nornir_nautobot.plugins.processors.fd_ceiling", lambda: 1000)
    monkeypatch.setattr("nornir_nautobot.plugins.processors.open_fd_count", lambda: 999)
    monkeypatch.setattr(BaseProcessor, "gc_fd_high_water", 0, raising=False)

    processor = BaseProcessor()
    for _ in range(50):
        _run_processor(processor, _passing_result())

    assert collect_calls == []


def test_fixed_interval_fallback(collect_calls, monkeypatch):
    """Platforms that cannot report a descriptor count fall back to the interval."""
    monkeypatch.setattr("nornir_nautobot.plugins.processors.open_fd_count", lambda: None)
    monkeypatch.setattr("nornir_nautobot.plugins.processors.fd_ceiling", lambda: None)
    monkeypatch.setattr(BaseProcessor, "gc_collect_interval", 5, raising=False)

    processor = BaseProcessor()
    for completed in range(1, 16):
        _run_processor(processor, _passing_result())
        assert len(collect_calls) == completed // 5


def test_unavailable_fd_count_is_a_noop_without_the_interval(collect_calls, monkeypatch):
    monkeypatch.setattr("nornir_nautobot.plugins.processors.open_fd_count", lambda: None)
    monkeypatch.setattr("nornir_nautobot.plugins.processors.fd_ceiling", lambda: None)

    processor = BaseProcessor()
    for _ in range(50):
        _run_processor(processor, _passing_result())

    assert collect_calls == []


def test_counter_is_threadsafe(collect_calls, monkeypatch):
    """The threaded runner calls task_instance_completed concurrently on one processor."""
    monkeypatch.setattr("nornir_nautobot.plugins.processors.open_fd_count", lambda: None)
    monkeypatch.setattr("nornir_nautobot.plugins.processors.fd_ceiling", lambda: None)
    monkeypatch.setattr(BaseProcessor, "gc_collect_interval", 10, raising=False)

    processor = BaseProcessor()

    def _worker():
        for _ in range(100):
            _run_processor(processor, _passing_result())

    threads = [threading.Thread(target=_worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # 8 threads x 100 instances = 800 completions, exactly 80 collections, no lost updates.
    assert len(collect_calls) == 80


def test_fd_ceiling_is_capped_at_select_fd_setsize(monkeypatch):
    """A large RLIMIT_NOFILE must not raise the ceiling past what select() can wait on."""
    monkeypatch.setattr("nornir_nautobot.plugins.processors.resource.getrlimit", lambda _which: (65536, 65536))
    assert fd_ceiling() == SELECT_FD_SETSIZE

    monkeypatch.setattr("nornir_nautobot.plugins.processors.resource.getrlimit", lambda _which: (256, 65536))
    assert fd_ceiling() == 256


def test_open_fd_count_reports_real_descriptors():
    before = open_fd_count()
    assert before is not None
    with open(os.devnull) as handle:  # noqa: F841
        assert open_fd_count() == before + 1
    assert open_fd_count() == before
