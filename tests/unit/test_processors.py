"""Pytest for exception frame clearing in the base processors."""

import gc
import logging
import traceback
import weakref
from unittest.mock import MagicMock

import pytest
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import MultiResult, Result

from nornir_nautobot.plugins.processors import (
    BaseLoggingProcessor,
    BaseProcessor,
    clear_result_exception_frames,
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
