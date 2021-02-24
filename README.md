# nornir_nautobot

## Overview

The nornir_nautobot project intends to solve two primary use cases.

* Providing a Nornir inventory that leverages Nautobot's API.
* A set of opinionated Nornir plugins.

The set of plugins intended to provide mechanisms to include common networking workflows that will help enable network automation. As
as example, there are method to get configurations or test network connectivity. Over time this will include functions to perform
actions such as get vlans, neighbors, protocols, etc.

## Getting Started

```shell
pip install nornir-nautobot
```

### 

To get started without a configuration file:

```python
    nornir_obj = InitNornir(
        inventory={
            "plugin": "NautobotInventory",
            "options": {
                "nautobot_url": os.getenv("NAUTOBOT_URL"),
                "nautobot_token": os.getenv("NAUTBOT_TOKEN"),
                "ssl_verify": False,
            },
        },
    )
```

1. As part of the initialization of the Nornir object, include the inventory key
2. Set the plugin to the name of `NautobotInventory`
3. Set the required options (if not already set via environment variables)

Accepted options include:

| Option            | Parameter         | Value                                                                                 | Default             |
| ----------------- | ----------------- | ------------------------------------------------------------------------------------- | ------------------- |
| Nautobot URL      | nautobot_url      | String - The base url of Nautobot (`http://localhost:8000` or `https://nautobot_url`) | env(NAUTOBOT_URL)   |
| Nautobot Token    | nautobot_token    | String - The token to authenticate to Nautobot API                                    | env(NAUTOBOT_TOKEN) |
| SSL Verify        | ssl_verify        | Boolean - True or False to verify SSL                                                 | True                |
| Filter Parameters | filter_parameters | Dictionary - Key/value pairs corresponding to Nautobot API searches                   | {}                  |


## Testing

In the early stages of testing since pynautobot is not available in a public state yet, it will be included via the `tests/packages` directory. This is **not** intended to be part of the actual packaging when things go live.

## Construct

Pynautobot will provide for the basic information that is required for Nornir to be able to leverage the inventory. The pynautobot object will also be made available at `host.data.pynautobot_object` to be able to access information provided from the _dcim devices_ endpoint.


## Task Plugins

The only task plugin currently is the "dispatcher" plugin. This plugin dispatches to the more specific OS specific functions. To demonstrate the primary components of the code:

#### Dispatcher Sender

```python
    try:
        driver_task = getattr(driver_class, method)
    except AttributeError:
        logger.log_failure(obj, f"Unable to locate the method {method} for {driver}")
        raise NornirNautobotException()

    result = task.run(task=driver_task, *args, **kwargs)
```

#### Dispatcher Receiver

```python
class NautobotNornirDriver:
    """Default collection of Nornir Tasks based on Napalm."""

    @staticmethod
    def get_config(task: Task, backup_file: str, *args, **kwargs) -> Result:
```

#### Calling Dispatcher

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

## Processor Plugins

Provided for convenience within the `nornir_nautobot.plugins.processors` is the `BaseProcessor` and `BaseLoggingProcessor` as boilerplate code for creating a custom processor.
