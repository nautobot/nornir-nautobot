# v3.0 Release Notes

## 3.3.1

* [179] Fixes Default Netmiko merge_config missing can_diff argument.

**Full Changelog**: https://github.com/nautobot/nornir-nautobot/compare/v3.3.0...v3.3.1

## 3.3.0

* [170] Add merge_config method to the Default Netmiko dispatcher.
* [176] Drop Python3.8 support.
* [174] Add a can_diff argument to *_config dispatcher methods to avoid logging sensitive data.
* [162] Add a extreme_exos dispatcher.
* [175] Add Scrapli support and a default Scrapli Dispatcher.
* [173] Add get_command(s) methods to all default dispatchers and change get_config to use get_command.

## New Contributors
* @EdificomSA made their first contribution in https://github.com/nautobot/nornir-nautobot/pull/162

**Full Changelog**: https://github.com/nautobot/nornir-nautobot/compare/v3.1.2...v3.3.0

## 3.2.0

* [#144] force the enable call to allow many cisco ios platforms to work
* [#149] Enhanced Jinja Error Handling and Stack Trace Logging by @jmpettit

### New Contributors
* @jmpettit made their first contribution in https://github.com/nautobot/nornir-nautobot/pull/149

**Full Changelog**: https://github.com/nautobot/nornir-nautobot/compare/v3.1.2...v3.2.0

## 3.1.2

- [#145](https://github.com/nautobot/nornir-nautobot/pull/145) Update httpx

## 3.1.1

- [#137](https://github.com/nautobot/nornir-nautobot/pull/137) Update to new pynautobot ssl verification

## 3.1.0

- [#131](https://github.com/nautobot/nornir-nautobot/pull/131) Updated logging output for Nornir

## 3.0.0

- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Changed the dispatcher method function signature - Breaking change
- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Restructured file layout to accommodate new dispatcher - Breaking change
- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Removed NornirLogger - Breaking Change
- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Updated to Nautobot loggin standard based on Python standard library logger
- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Migrated filters to Nautobot 2.0 standards, e.g. location
- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Added error codes e.g. E1001, to better facilitate troubleshooting
- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Added ability to control what `tcp_port` number to use in the `check_connectivity` method
- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Updated to latest NTC development standards and updated dependencies
