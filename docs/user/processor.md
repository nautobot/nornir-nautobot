---
hide:
  - navigation
---
# Processor Plugins

Provided for convenience within the `nornir_nautobot.plugins.processors` is the `BaseProcessor` and `BaseLoggingProcessor` as boilerplate code for creating a custom processor.

## Releasing Exception Frames

When a task fails, Nornir stores the live exception object on the `Result`, and that result stays in the `AggregatedResult` until the play finishes. The exception's traceback pins the frames of whatever raised it, including the connection frames of the underlying driver and any resources their local variables hold. With Paramiko, for example, a connection made through an SSH `ProxyJump` or `ProxyCommand` holds three open pipes that cannot be garbage collected while those frames are alive, so a play with many connection failures can exhaust the process's file descriptor limit before it ends.

To prevent this, `BaseProcessor.task_instance_completed` calls `clear_result_exception_frames()` on the `MultiResult` it is given. That walks every stored exception, following `__cause__`, `__context__`, and the sub-results of a `NornirSubTaskError`, and drops the local variables held by each traceback frame. `BaseLoggingProcessor` inherits this behavior through `super()`.

A custom processor that overrides `task_instance_completed` should either call `super().task_instance_completed(task, host, result)` or call the helper directly:

```python
from nornir_nautobot.plugins.processors import BaseLoggingProcessor, clear_result_exception_frames


class MyProcessor(BaseLoggingProcessor):
    def task_instance_completed(self, task, host, result):
        # custom handling
        clear_result_exception_frames(result)
```

Only the frame locals are dropped. The formatted traceback string that Nornir writes to `Result.result` and the exception message itself are unchanged, so nothing is lost from logs or error reporting. The one behavioral difference is that post-mortem debugging of a completed Nornir result no longer has access to frame local variables.