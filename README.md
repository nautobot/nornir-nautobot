
<div style="text-align: center;"> 
  <h1>Nornir Nautobot</h1>
</div>  
<p align="center">
  <a href="https://github.com/nautobot/nornir-nautobot/actions"><img src="https://github.com/nautobot/nornir-nautobot/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="https://pypi.org/project/nornir-nautobot/"><img src="https://img.shields.io/pypi/v/nornir-nautobot"></a>
  <a href="https://pypi.org/project/nornir-nautobot/"><img src="https://img.shields.io/pypi/dm/nornir-nautobot"></a>
  <br>
</p>


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

[Inventory](inventory/inventory.md)

## Processor Plugin

This is an opinionated plugin to help with network automation workflows with Nautobot.

[Processor Plugin](processor/processor.md)

## Task Plugin

The task plugin helps with dispatching specific functions with multiple underlying OS.

[Task Plugin](task/task.md)