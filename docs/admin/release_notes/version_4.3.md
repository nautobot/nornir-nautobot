
# v4.3 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Expanded offline command support, adding Git-sourced command output to the NAPALM and Scrapli dispatchers and a `force_offline` kwarg on `get_command` to bypass the `offline_commands` config context.

<!-- towncrier release notes start -->

## [v4.3.0 (2026-07-16)](https://github.com/nautobot/nornir-nautobot/releases/tag/v4.3.0)

### Added

- [#289](https://github.com/nautobot/nornir-nautobot/issues/289) - Added Git-sourced offline command output support to the NAPALM and Scrapli dispatchers.
- [#289](https://github.com/nautobot/nornir-nautobot/issues/289) - Added a force_offline kwarg to get_command on the Netmiko, NAPALM, and Scrapli dispatchers to force reading command output from a Git file, bypassing the offline_commands config context.

### Fixed

- [#291](https://github.com/nautobot/nornir-nautobot/issues/291) - Fixed the save step in the Netmiko `merge_config` logging a discarded error message on failure, and added a log message confirming when the configuration save has completed.
