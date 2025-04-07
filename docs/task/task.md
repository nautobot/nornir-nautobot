# Task Plugins

The only task plugin currently is the "dispatcher" plugin. This plugin dispatches to the more specific OS specific functions. To demonstrate the primary components of the code:

## Dispatcher Sender

- If exists check `custom_dispatcher`, for network_driver, if a custom_dispatcher is used but not found, fail immediately
- Check for framework & driver `f"nornir_nautobot.plugins.tasks.dispatcher.{network_driver}.{framework.title()}{network_driver_title}"`
- Check for default, e.g. `f"nornir_nautobot.plugins.tasks.dispatcher.default.{framework.title()}Default"`

!!! info
    Where `framework` is a library like `netmiko` or `napalm` and `network_driver` is the platform like `cisco_ios` or `arista_eos`.

This may seem like a lot, but it essentially can be broken down to:

- If there is a custom_dispatcher, **only** use that
- Check for the `framework` and `network_driver`
- Check for the `framework`'s default

For completeness here is the referenced code as of October 2023.

```python
    custom_dispatcher = ""
    if kwargs.get("custom_dispatcher"):
        custom_dispatcher = kwargs["custom_dispatcher"]
        del kwargs["custom_dispatcher"]

    logger.debug(f"Dispatcher process started for {task.host.name} ({task.host.platform})")

    network_driver = task.host.platform
    network_driver_title = snake_to_title_case(network_driver)
    framework_path = (
        f"nornir_nautobot.plugins.tasks.dispatcher.{network_driver}.{framework.title()}{network_driver_title}"
    )
    framework_default_path = f"nornir_nautobot.plugins.tasks.dispatcher.default.{framework.title()}Default"

    if custom_dispatcher:
        driver_class = import_string(custom_dispatcher)
        checked_path = [custom_dispatcher]
    elif import_string(framework_path):
        driver_class = import_string(framework_path)
        checked_path = [framework_path]
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
    obj=obj,
    logger=logger,
    method="get_config",
    framework="netmiko",
    name="SAVE BACKUP CONFIGURATION TO FILE",
    backup_file=backup_file,
    remove_lines=remove_regex_dict.get(obj.platform.network_driver, []),
    substitute_lines=replace_regex_dict.get(obj.platform.network_driver, []),
)
```

The dispatcher expects the two primary objects, the `obj` and `logger` objects. The `obj` object should be a Device model instance. The logger must conform to the standard Python logger, in that it should take is `message` as the first arg and allow a dictionary called `extra`.

Each task will raise a `NornirNautobotException` for known issues. Using a custom processor, the user can predict when it was an well known error.


## Check Connectivity Configuration

The check connectivity receiver will send attempt to tcp ping the port based on the following order or precedence.

- Prefer `obj.cf["tcp_port"]` if is a valid integer
- Prefer `obj.get_config_context()["tcp_port"]` if is a valid integer
- Prefer cls.tcp_port, which by default is defined in `DispatcherMixin` as 22

In this code you can see how it is set.

```python
class DispatcherMixin:

    tcp_port = 22

    @classmethod
    def _get_tcp_port(cls, obj) -> str:
        custom_field = obj.cf.get("tcp_port")
        if isinstance(custom_field, int):
            return custom_field
        config_context = obj.get_config_context().get("tcp_port")
        if isinstance(config_context, int):
            return config_context
        return cls.tcp_port
```

## Netmiko Show Running Config Command

The Netmiko `show_command` tells Netmiko which command to use to get the config, generally used to backup the configuration. You can override the default provided based on this logic:

- Prefer `obj.cf["config_command"]` if it is a valid string.
- Prefer `obj.get_config_context()["config_command"]` if it is a valid string.
- Use the default command defined in in your Netmiko dispatcher, often defaulting to `NetmikoDefault` which sets `show run`.

Here is the implementation:

```python
class NetmikoDefault(DispatcherMixin):

    config_command = "show run"

    @classmethod
    def _get_config_command(cls, obj) -> str:
        custom_field = obj.cf.get("config_command")
        if isinstance(custom_field, str):
            return custom_field
        config_context = obj.get_config_context().get("config_command")
        if isinstance(config_context, str):
            return config_context
        return cls.config_command
```

## Environment Variables

| Environment Variable | Explanation |
| ----- | ----------- |
| NORNIR_NAUTOBOT_REVERT_IN_SECONDS  | Amount in seconds to revert if a config based method fails. |
| NORNIR_NAUTOBOT_NETMIKO_ENABLE_DEFAULT | Override the default(True) to not automatically call the `enable` function before running commands. |
