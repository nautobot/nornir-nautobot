# Nornir Nautobot

Nornir-Nautobot is a set of utilities to help interact with Nautobot via Nornir.

## Installation

To install Nornir Nautobot install via Python PIP:

```shell
pip install nornir-nautobot
```

## Inventory

The inventory plugin is used to gather inventory from a Nautobot instance. This queries the DCIM endpoint to gather information about the devices.  

[Inventory](inventory/inventory.md)

## Processor Plugin

This is an opinionated plugin to help with network automation workflows with Nautobot.

[Processor Plugin](plugins/plugins.md)

## Task Plugin

The task plugin helps with dispatching specific functions with multiple underlying OS.

[Task Plugin](task/task.md)
