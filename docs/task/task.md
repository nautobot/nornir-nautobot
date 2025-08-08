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

- First prefer `obj.cf["config_command"]` if it is set and a valid string, which is to say if a custom field named `config_command` is present it should be preferred.
- Second prefer `obj.get_config_context()["config_command"]` if it is set and a valid string, which is to say if a config context is rendered for this device named `config_command` is present it should be preferred.
- Finally default to the command defined in your Netmiko dispatcher, often defaulting to `NetmikoDefault` which sets it to `show run`.

Here is the implementation:

```python
class NetmikoDefault(DispatcherMixin):

    config_command = "show run"

    @classmethod
    def _get_config_command(cls, obj) -> str:
        custom_field = obj.cf.get("config_command")
        if custom_field and isinstance(custom_field, str):
            return custom_field
        config_context = obj.get_config_context().get("config_command")
        if config_context and isinstance(config_context, str):
            return config_context
        return cls.config_command
```

## Get command outputs through git repository

Raw command outputs stored in a Git repository can be used in scenarios where Nautobot is not able to connect directly to the network devices. This is useful for disconnected or air-gapped environments, lab setups, or testing purposes.

The feature is integrated into the `NetmikoDefault` dispatcher and is controlled by the `offline_commands` setting with the following precedence:

1. `obj.cf["offline_commands"]` — if it exists and is a valid boolean value.
2. `obj.get_config_context()["offline_commands"]` — if it exists and is a valid boolean value.
3. `cls.offline_commands` — the default class attribute defined in `NetmikoDefault`, which defaults to `False`.

When enabled, the dispatcher attempts to read the expected command output from the filesystem (via the keyword argument command_file_path) instead of executing the command on a live device. This requires the output files to be named in a filesystem-safe format.

The utility function `nornir_nautobot.utils.helpers.command_to_filename` is provided to help convert a command string into a valid filename. Here's how it works:

```python
def command_to_filename(command, replacement="_"):
    """
    Convert a command string into a filesystem-safe filename.

    This function sanitizes a command string so it can safely be used as a filename by:
    1. Normalizing Unicode characters to their ASCII equivalents.
    2. Replacing the pipe symbol '|' (with or without surrounding spaces) with two replacement characters.
    3. Replacing characters that are illegal in most filesystems (e.g., / : * ? " < >) with the replacement character.
    4. Replacing all spaces with the replacement character.

    Args:
        command (str): The input command string to sanitize.
        replacement (str): The character to use as a substitute for illegal or special characters. Default is underscore ('_').

    Returns:
        str: A sanitized, ASCII-only, filesystem-safe version of the command string suitable for use as a filename.
    """
```

This ensures consistent and safe naming of command output files across different operating systems and Git repositories.

## Environment Variables

| Environment Variable | Explanation |
| ----- | ----------- |
| NORNIR_NAUTOBOT_REVERT_IN_SECONDS  | Amount in seconds to revert if a config based method fails. |
| NORNIR_NAUTOBOT_NETMIKO_ENABLE_DEFAULT | Override the default(True) to not automatically call the `enable` function before running commands. |
