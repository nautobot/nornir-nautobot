---
hide:
  - navigation
---
# Task Plugins

The only task plugin currently is the "dispatcher" plugin. This plugin dispatches to the more specific OS specific functions. To demonstrate the primary components of the code:

## Dispatcher Sender

- If exists check `custom_dispatcher`, for network_driver (fail if not found)
- Check for framework & driver `f".dispatcher.{framework}{network_driver.titlecase()}"`
- Check for default, e.g. `f".dispatcher.{framework}default"`

!!! info
    Where `framework` is a library like `netmiko` or `napalm` and `network_driver` is the platform like `cisco_ios` or `arista_eos`.

```python
    if not kwargs.get("custom_dispatcher"):
        custom_dispatcher = {}
    logger.log_debug(f"Dispatcher process started for {task.host.name} ({task.host.platform.network_driver})")

    network_driver = task.host.platform.network_driver
    network_driver_title = snake_to_title_case(network_driver)
    custom_dispatcher_path = [custom_dispatcher.get(network_driver)]
    framework_path = f"nornir_nautobot.plugins.tasks.dispatcher.{network_driver}.{framework}{network_driver_title}"
    framework_default_path = f"nornir_nautobot.plugins.tasks.dispatcher.default.{framework}Default"

    if custom_dispatcher.get(network_driver):
        driver_class = import_string(custom_dispatcher_path)
        checked_path = [custom_dispatcher_path]
    elif import_string(framework_path):
        driver_class = import_string(framework_path)
    else:
        driver_class = import_string(framework_default_path)
        checked_path = [framework_path, framework_default_path]

    result = task.run(task=driver_task, *args, **kwargs)
```

## Dispatcher Receiver

```python
class NautobotNornirDriver:
    """Default collection of Nornir Tasks based on Napalm."""

    @classmethod
    def get_config(cls, task: Task, backup_file: str, *args, **kwargs) -> Result:
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

The dispatcher expects the two primary objects, the `obj` and `logger` objects. The `obj` object should be a Device model instance. The logger should be `NornirLogger` instance which is imported from `nornir_nautobot.utils.logger`. This logging object optionally takes in a Nautobot Job object named nautobot_job. This is for use within the Nautobot platform Jobs. 

Each task will raise a `NornirNautobotException` for known issues. Using a custom processor, the user can predict when it was an well known error.


## Check Connectivity Configuration

The check connectivity receiver will send attempt to tcp ping the port based on the following order or precedence.

- Prefer `task.data["custom_field_data"]["tcp_port"]` if is a valid integer
- Prefer `task.data["config_context_data"]["tcp_port"]` if is a valid integer
- Prefer cls.tcp_port, which by default is defined in `DispatcherMixin` as 22

In this code you can see how it is set.

```python
class DispatcherMixin:

    tcp_port = 22

    @classmethod
    def _get_tcp_port(cls, task, obj) -> str:
        custom_field = task.data.get("custom_field_data", {}).get("tcp_port")
        if isinstance(custom_field, int):
            return custom_field
        config_context = task.data.get("config_context_data", {}).get("tcp_port")
        if isinstance(config_context, int):
            return config_context
        return cls.tcp_port
```