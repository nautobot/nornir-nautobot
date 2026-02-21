# v3.3 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 3.3.1

* [179](https://github.com/nautobot/nornir-nautobot/issues/179) Fixes Default Netmiko merge_config missing can_diff argument.

## 3.3.0

* [170](https://github.com/nautobot/nornir-nautobot/issues/170) Add merge_config method to the Default Netmiko dispatcher.
* [176](https://github.com/nautobot/nornir-nautobot/issues/176) Drop Python3.8 support.
* [174](https://github.com/nautobot/nornir-nautobot/issues/174) Add a can_diff argument to *_config dispatcher methods to avoid logging sensitive data.
* [162](https://github.com/nautobot/nornir-nautobot/issues/162) Add a extreme_exos dispatcher.
* [175](https://github.com/nautobot/nornir-nautobot/issues/175) Add Scrapli support and a default Scrapli Dispatcher.
* [173](https://github.com/nautobot/nornir-nautobot/issues/173) Add get_command(s) methods to all default dispatchers and change get_config to use get_command.

## New Contributors
* @EdificomSA made their first contribution in https://github.com/nautobot/nornir-nautobot/pull/162
