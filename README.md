# nornir_nautobot

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

## Build Status

| Branch  | Status                                                                                                                               |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| main    | [![Build Status](https://travis-ci.com/nautobot/nornir-nautobot.svg?branch=main)](https://travis-ci.com/nautobot/nornir-nautobot)    |
| develop | [![Build Status](https://travis-ci.com/nautobot/nornir-nautobot.svg?branch=develop)](https://travis-ci.com/nautobot/nornir-nautobot) |
## Overview

The nornir_nautobot project intends to solve two primary use cases.

* Providing a Nornir inventory that leverages Nautobot's API.
* A set of opinionated Nornir plugins.

The set of plugins intend to provide mechanisms to include common networking workflows that will help enable network automation. As an example, there are method to get configurations or test network connectivity. Over time this will include functions to perform actions such as get vlans, neighbors, protocols, etc.

## Getting Started

```shell
pip install nornir-nautobot
```

## Documentation Link

The documentation can be found on [Read the Docs](https://nornir-nautobot.readthedocs.io/en/latest/)

## Nautobot

Nautobot documentation is available at [Nautobot Read the Docs](https://nautobot.readthedocs.io/en/latest/)
