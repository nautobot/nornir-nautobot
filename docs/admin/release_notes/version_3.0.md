# v3.0 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# v3.4 Release Notes

## Release Overview

- Migrate the library to newest dev standards as of 2025
- Adds Offline command getters and generic Git dispatcher functionality for pulling in files from a Nautobot Git repository.
- Move config_command to use Netutils functionality to make it dynamic, and more flexible within Nautobot and Golden Config.

## [v3.4.0 (2025-08-28)](https://github.com/networktocode/nornir-nautobot/releases/tag/v3.4.0)

### Added

- [#185](https://github.com/nautobot/nornir-nautobot/issues/185) - Add a check for Permission denied for role that is seen on Cisco NXOS.
- [#195](https://github.com/nautobot/nornir-nautobot/issues/195) - Adds Offline command getters and generic Git dispatcher functionality for pulling in files from a Nautobot Git repository.
- [#204](https://github.com/nautobot/nornir-nautobot/issues/204) - Move config_command to use Netutils functionality to make it dynamic.
- [#210](https://github.com/nautobot/nornir-nautobot/issues/210) - Added `get_command_with_prompts` to the `NetmikoDefault` dispatcher for sending commands and reacting to prompts.

### Removed

- Remove the code-references file generation and script as its not helpful in this library.

### Fixed

- [#199](https://github.com/nautobot/nornir-nautobot/issues/199) - Create better logging for Jinja issues.
- [#201](https://github.com/nautobot/nornir-nautobot/issues/201) - Fixed the development standards to use 2025 standards.
- [#202](https://github.com/nautobot/nornir-nautobot/issues/202) - Relaxed multiple dependencies to allow for update up until the next major version.
- Fixed incorrect links throughout docs, and add missing logo.

### Documentation

- [#209](https://github.com/nautobot/nornir-nautobot/issues/209) - Updated the error code documentation for all default dispatcher error codes.

### Housekeeping

- [#188](https://github.com/nautobot/nornir-nautobot/issues/188) - Update dependencies to be more explicit.
- Add missing towncrier_template and update poetry's towncrier settings.
- Few last fixes for docs, a CI.
- Go through changelog from before towncrier and add them for the next release.

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


## 3.2.0

* [144](https://github.com/nautobot/nornir-nautobot/issues/144) force the enable call to allow many cisco ios platforms to work
* [149](https://github.com/nautobot/nornir-nautobot/issues/149) Enhanced Jinja Error Handling and Stack Trace Logging by @jmpettit

### New Contributors
* @jmpettit made their first contribution in https://github.com/nautobot/nornir-nautobot/pull/149


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
