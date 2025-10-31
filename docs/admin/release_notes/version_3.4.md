# v3.4 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a
Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

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