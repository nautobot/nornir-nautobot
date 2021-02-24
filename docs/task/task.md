# Task Plugins

The only task plugin currently is the "dispatcher" plugin. This plugin dispatches to the more specific OS specific functions. To demonstrate the primary components of the code:

## Dispatcher Sender

```python
    try:
        driver_task = getattr(driver_class, method)
    except AttributeError:
        logger.log_failure(obj, f"Unable to locate the method {method} for {driver}")
        raise NornirNautobotException()

    result = task.run(task=driver_task, *args, **kwargs)
```

## Dispatcher Receiver

```python
class NautobotNornirDriver:
    """Default collection of Nornir Tasks based on Napalm."""

    @staticmethod
    def get_config(task: Task, backup_file: str, *args, **kwargs) -> Result:
```

## Calling Dispatcher

```python
task.run(
    task=dispatcher,
    name="SAVE BACKUP CONFIGURATION TO FILE",
    method="get_config",
    obj=obj,
    logger=logger,
    backup_file=backup_file,
    remove_lines=global_settings,
    substitute_lines=substitute_lines,
)
```

The dispatcher expects the two primary objects, the `obj` and `logger` objects. The `obj` object should be a Device model instance. The logger should be `NornirLogger` instance which is imported from `nornir_nautobot.utils.logger`. This logging object optionally takes in a Nautobot job_result object. This is for use within the Nautobot platform Jobs. 

Each task will raise a `NornirNautobotException` for known issues. Using a custom processor, the user can predict when it was an well known error.
