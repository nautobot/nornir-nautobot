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

## Periodic Garbage Collection

Some connection drivers hold operating system resources inside reference cycles, so calling `close()` or `disconnect()` does not release them immediately; only a generational garbage collection does.

Netmiko connections made through an SSH proxy are one example. Netmiko builds a `paramiko.ProxyCommand` for each device, which spawns an `ssh` subprocess with three pipes attached, and `ProxyCommand.close()` sends `SIGTERM` without closing those pipes ([paramiko#2568](https://github.com/paramiko/paramiko/issues/2568)). The pipes stay open until Paramiko's `Transport` and `Channel` objects, which refer to each other, are collected as a cycle.

Over a long play these accumulate faster than CPython's default collection schedule reclaims them, and the process can reach its open file limit while tasks are still succeeding.

`BaseProcessor.task_instance_completed` guards against this by checking how many descriptors the process holds and collecting only when that number approaches the usable ceiling.

```python
class MyProcessor(BaseProcessor):
    gc_fd_high_water = 0.5  # collect sooner, default is 0.7
    # gc_fd_high_water = 0  # disable entirely
```

The ceiling is the process's `RLIMIT_NOFILE`, capped at 1024. The cap matters because `select()` cannot wait on a descriptor numbered at or above `FD_SETSIZE`, so a driver whose event loop uses it (Paramiko's `ProxyCommand` does) fails at that number regardless of how high the limit is raised.

If a collection does not bring the count back below the mark, the descriptors are in use rather than collectable. Collecting again would not help, so the check pauses for `gc_cooldown` task instances before trying again.

On a platform that cannot report a descriptor count, such as Windows, the check is skipped. Set `gc_collect_interval` to collect every N task instances instead:

```python
class MyProcessor(BaseProcessor):
    gc_collect_interval = 20
```

A processor that overrides `task_instance_completed` without calling `super()` opts out of both the collection and the frame clearing described above.
