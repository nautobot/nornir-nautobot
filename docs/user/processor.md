---
hide:
  - navigation
---
# Processor Plugins

Provided for convenience within the `nornir_nautobot.plugins.processors` is the `BaseProcessor` and `BaseLoggingProcessor` as boilerplate code for creating a custom processor.

Both base processors do two pieces of cleanup for you after every task instance. **If you do not override `task_instance_completed`, there is nothing you need to do — skip to [Tuning](#tuning).**

## Releasing Exception Frames

**In short:** when a device task fails, Python keeps the whole failed call stack alive for the rest of the play, and anything that stack was holding — including open network connections — stays open with it. The base processor throws away the parts that hold resources and keeps the parts you read in logs.

If you override `task_instance_completed`, call `super()` so this still happens:

```python
class MyProcessor(BaseLoggingProcessor):
    def task_instance_completed(self, task, host, result):
        # custom handling
        super().task_instance_completed(task, host, result)
```

Or call the helper yourself if you would rather not call `super()`:

```python
from nornir_nautobot.plugins.processors import BaseLoggingProcessor, clear_result_exception_frames


class MyProcessor(BaseLoggingProcessor):
    def task_instance_completed(self, task, host, result):
        # custom handling
        clear_result_exception_frames(result)
```

**Your error messages and tracebacks are unaffected.** The only thing lost is the ability to inspect local variables of a completed result in a debugger.

??? note "How this works"

    When a task fails, Nornir stores the live exception object on the `Result`, and that result stays in the `AggregatedResult` until the play finishes. The exception's traceback pins the frames of whatever raised it, including the connection frames of the underlying driver and any resources their local variables hold. With Paramiko, for example, a connection made through an SSH `ProxyJump` or `ProxyCommand` holds three open pipes that cannot be garbage collected while those frames are alive, so a play with many connection failures can exhaust the process's file descriptor limit before it ends.

    To prevent this, `BaseProcessor.task_instance_completed` calls `clear_result_exception_frames()` on the `MultiResult` it is given. That walks every stored exception, following `__cause__`, `__context__`, and the sub-results of a `NornirSubTaskError`, and drops the local variables held by each traceback frame. `BaseLoggingProcessor` inherits this behavior through `super()`.

    Only the frame locals are dropped. The formatted traceback string that Nornir writes to `Result.result` and the exception message itself are unchanged, so nothing is lost from logs or error reporting. The one behavioral difference is that post-mortem debugging of a completed Nornir result no longer has access to frame local variables.

## Periodic Garbage Collection

**In short:** some SSH connections do not actually release their operating system resources when you close them. Python only reclaims them during a cleanup pass that it runs on its own schedule, and on a long play that schedule is too slow, so the process can run out of open files while tasks are still succeeding. The base processor watches the count of open files and runs that cleanup pass early when the number gets high.

You should not need to change anything. See [Tuning](#tuning) if you do.

??? note "How this works"

    Some connection drivers hold operating system resources inside reference cycles, so calling `close()` or `disconnect()` does not release them immediately; only a generational garbage collection does.

    Netmiko connections made through an SSH proxy are one example. Netmiko builds a `paramiko.ProxyCommand` for each device, which spawns an `ssh` subprocess with three pipes attached, and `ProxyCommand.close()` sends `SIGTERM` without closing those pipes ([paramiko#2568](https://github.com/paramiko/paramiko/issues/2568)). The pipes stay open until Paramiko's `Transport` and `Channel` objects, which refer to each other, are collected as a cycle.

    Over a long play these accumulate faster than CPython's default collection schedule reclaims them, and the process can reach its open file limit while tasks are still succeeding.

    `BaseProcessor.task_instance_completed` guards against this by checking how many descriptors the process holds and collecting only when that number approaches the usable ceiling.

    The ceiling is the process's `RLIMIT_NOFILE`, capped at 1024. The cap matters because `select()` cannot wait on a descriptor numbered at or above `FD_SETSIZE`, so a driver whose event loop uses it (Paramiko's `ProxyCommand` does) fails at that number regardless of how high the limit is raised.

    If a collection does not bring the count back below the mark, the descriptors are in use rather than collectable. Collecting again would not help, so the check pauses for `gc_cooldown` task instances before trying again.

## Tuning

Set these as class attributes on your processor. The defaults are fine for most plays.

| Attribute | Default | What it does |
| --- | --- | --- |
| `gc_fd_high_water` | `0.7` | Clean up once open files reach this fraction of the limit. Lower cleans up sooner. `0` turns the check off. |
| `gc_cooldown` | `50` | If a cleanup frees nothing, wait this many task instances before checking again. |

```python
class MyProcessor(BaseProcessor):
    gc_fd_high_water = 0.5  # collect sooner, default is 0.7
```

If the open-file count cannot be read at all (neither `/proc/self/fd` nor `/dev/fd` is available), the check is skipped and a warning is logged once, so the loss of protection is visible rather than silent.

**A processor that overrides `task_instance_completed` without calling `super()` opts out of both the garbage collection and the frame clearing described above.**
