# Changelog

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


## v2.6.1

- [#108](https://github.com/nautobot/nornir-nautobot/pull/108) Add enable threading option
- [#109](https://github.com/nautobot/nornir-nautobot/pull/109) Patch merge_config methods return values


## v2.6.0

- [#96](https://github.com/nautobot/nornir-nautobot/pull/96) Changes backup_file to be conditional for get_config
- [#98](https://github.com/nautobot/nornir-nautobot/pull/98) Adds merge_config method

## v2.5.0

- [#93](https://github.com/nautobot/nornir-nautobot/pull/93) Updates Nornir-Netmiko to 1.0.0 release
- [#97](https://github.com/nautobot/nornir-nautobot/pull/97) Adds Jinja Environment option to generate_config

## v2.4.0

- [#61](https://github.com/nautobot/nornir-nautobot/pull/61) Be more clear on error messages by @itdependsnetworks
- [#66](https://github.com/nautobot/nornir-nautobot/pull/66) Add basic typing to the methods in logger by @KalleDK
- [#75](https://github.com/nautobot/nornir-nautobot/pull/75) Documentation refactor by @susanhooks
- [#77](https://github.com/nautobot/nornir-nautobot/pull/77) added ICX/Fastiron Nornir Driver by @pato23arg
- [#78](https://github.com/nautobot/nornir-nautobot/pull/78) Fix RTD docs build by @cmsirbu
- [#83](https://github.com/nautobot/nornir-nautobot/pull/83) Adds provision_config method by @joewesch
- [#76](https://github.com/nautobot/nornir-nautobot/pull/76) Mikrotik RouterOS CLI Support by @pato23arg
- [#79](https://github.com/nautobot/nornir-nautobot/pull/79) Mikrotik RouterOS API support by @pato23arg
- [#85](https://github.com/nautobot/nornir-nautobot/pull/85) Ruckus Smartzone WLC and Access Point Driver by @pato23arg

## New Contributors
* @KalleDK made their first contribution in https://github.com/nautobot/nornir-nautobot/pull/66
* @susanhooks made their first contribution in https://github.com/nautobot/nornir-nautobot/pull/75
* @pato23arg made their first contribution in https://github.com/nautobot/nornir-nautobot/pull/77
* @cmsirbu made their first contribution in https://github.com/nautobot/nornir-nautobot/pull/78
* @joewesch made their first contribution in https://github.com/nautobot/nornir-nautobot/pull/83

## v2.3.0

- [#67](https://github.com/nautobot/nornir-nautobot/pull/67) fix pylint, tests, and drop py36 support #67

## v2.2.0

- [#41](https://github.com/nautobot/nornir-nautobot/pull/41) Added jinja2 filter pass to generate config
- [#42](https://github.com/nautobot/nornir-nautobot/pull/42) Added Cisco ASA mapping to default mapping

## v2.1.2

- [#40](https://github.com/nautobot/nornir-nautobot/pull/40) Fix nornir inventory defaults

## v2.1.1

- [#31](https://github.com/nautobot/nornir-nautobot/pull/31) Migrate from Travis-CI to GitHub Actions for CI
- [#32](https://github.com/nautobot/nornir-nautobot/pull/32) Fix data population when generating configurations from the dispatcher

## v2.1.0

- [#26](https://github.com/nautobot/nornir-nautobot/pull/26) Updates in poetry packaging for pre 1.0.0 dependencies in Nornir to allow all new up to 1.0.0 releases

## v2.0.3

- [#24](https://github.com/nautobot/nornir-nautobot/pull/24) Change import mechanism / changes deprecated function

## v2.0.1

- [#20](https://github.com/nautobot/nornir-nautobot/pull/20) Fixes inventory failure when platform is not defined for a device
## v2.0.0

- [#18](https://github.com/nautobot/nornir-nautobot/pull/18) Migrates functions to new NTC netutils library, which is removing methods previously available:
    - compliance
    - make_folder
    - hostname_resolves
    - test_tcp_port
    - is_ip

## v0.1.0 - 2020-12-27

Initial release
