# Nornir Nautobot

<p align="center">
  <img src="https://raw.githubusercontent.com/nautobot/nornir-nautobot/develop/docs/images/nautobot_logo.svg" class="logo" height="200px">
  <br>
  <a href="https://github.com/nautobot/nornir-nautobot/actions"><img src="https://github.com/nautobot/nornir-nautobot/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="https://nornir-nautobot.readthedocs.io/en/latest"><img src="https://readthedocs.org/projects/nornir-nautobot/badge/"></a>
  <a href="https://pypi.org/project/nornir-nautobot/"><img src="https://img.shields.io/pypi/v/nornir-nautobot"></a>
  <a href="https://pypi.org/project/nornir-nautobot/"><img src="https://img.shields.io/pypi/dm/nornir-nautobot"></a>
  <br>
</p>

## Overview

Nornir-Nautobot is a set of utilities to help interact with Nautobot via Nornir. The nornir_nautobot project intends to solve two primary use cases.

* Providing a Nornir inventory that leverages Nautobot's API.
* A set of opinionated Nornir plugins.

The set of plugins intend to provide mechanisms to include common networking workflows that will help enable network automation. As an example, there are method to get configurations or test network connectivity. Over time this will include functions to perform actions such as get vlans, neighbors, protocols, etc.

## Documentation

Full web-based HTML documentation for this library can be found over on the [Nornir-Nautobot Docs](https://nornir-nautobot.readthedocs.io) website:

- [User Guide](https://nornir-nautobot.readthedocs.io/en/latest/user/lib_overview/) - Overview, Using the library, Getting Started.
- [Administrator Guide](https://nornir-nautobot.readthedocs.io/en/latest/admin/install/) - How to Install, Configure, Upgrade, or Uninstall the library.
- [Developer Guide](https://nornir-nautobot.readthedocs.io/en/latest/dev/contributing/) - Extending the library, Code Reference, Contribution Guide.
- [Release Notes / Changelog](https://nornir-nautobot.readthedocs.io/en/latest/admin/release_notes/).
- [Frequently Asked Questions](https://nornir-nautobot.readthedocs.io/en/latest/user/faq/).

### Contributing to the Docs

All the Markdown source for the library documentation can be found under the [docs](https://github.com/nautobot/nornir-nautobot/tree/develop/docs) folder in this repository. For simple edits, a Markdown capable editor is sufficient - clone the repository and edit away.

If you need to view the fully generated documentation site, you can build it with [mkdocs](https://www.mkdocs.org/). A container hosting the docs will be started using the invoke commands (details in the [Development Environment Guide](https://nornir-nautobot.readthedocs.io/en/latest/dev/dev_environment/#docker-development-environment)) on [http://localhost:8001](http://localhost:8001). As your changes are saved, the live docs will be automatically reloaded.

Any PRs with fixes or improvements are very welcome!

## Questions

For any questions or comments, please check the [FAQ](https://nornir-nautobot.readthedocs.io/en/latest/user/faq/) first. Feel free to also swing by the [Network to Code Slack](https://networktocode.slack.com/) (channel `#networktocode`), sign up [here](http://slack.networktocode.com/) if you don't have an account.
