# Nornir Nautobot
[![GitHub Actions](https://github.com/nautobot/nornir-nautobot/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/nautobot/nornir-nautobot/actions)
[![PyPI Version](https://img.shields.io/pypi/v/nornir-nautobot)](https://pypi.org/project/nornir-nautobot/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/nornir-nautobot)](https://pypi.org/project/nornir-nautobot/)

Nornir-Nautobot is a set of utilities to help interact with Nautobot via Nornir. The nornir_nautobot project intends to solve two primary use cases.

* Providing a Nornir inventory that leverages Nautobot's API.
* A set of opinionated Nornir plugins.

The set of plugins intend to provide mechanisms to include common networking workflows that will help enable network automation. As an example, there are method to get configurations or test network connectivity. Over time this will include functions to perform actions such as get vlans, neighbors, protocols, etc.

# Installation

To install Nornir Nautobot install via Python PIP:

```shell
pip install nornir-nautobot
```
## Inventory

The inventory plugin is used to gather inventory from a Nautobot instance. This queries the DCIM endpoint to gather information about the devices.  

[Inventory](https://docs.nautobot.com/projects/nornir-nautobot/en/latest/inventory/inventory/)

## Processor Plugin

This is an opinionated plugin to help with network automation workflows with Nautobot.

[Processor Plugin](https://docs.nautobot.com/projects/nornir-nautobot/en/latest/processor/processor/)

## Task Plugin

The task plugin helps with dispatching specific functions with multiple underlying OS.

[Task Plugin](https://docs.nautobot.com/projects/nornir-nautobot/en/latest/task/task/)