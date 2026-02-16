# v3.0 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 3.0.0

- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Changed the dispatcher method function signature - Breaking change
- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Restructured file layout to accommodate new dispatcher - Breaking change
- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Removed NornirLogger - Breaking Change
- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Updated to Nautobot loggin standard based on Python standard library logger
- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Migrated filters to Nautobot 2.0 standards, e.g. location
- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Added error codes e.g. E1001, to better facilitate troubleshooting
- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Added ability to control what `tcp_port` number to use in the `check_connectivity` method
- [#107](https://github.com/nautobot/nornir-nautobot/pull/107) Updated to latest NTC development standards and updated dependencies
