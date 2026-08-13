# v4.4 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones

<!-- towncrier release notes start -->

# v4.4 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

## [v4.4.0 (2026-08-13)](https://github.com/nautobot/nornir-nautobot/releases/tag/v4.4.0)

### Added

- [#298](https://github.com/nautobot/nornir-nautobot/issues/298) - Added support for Jinja template rendering with `substitute_lines` in the `get_config` task.

### Dependencies

- [#295](https://github.com/nautobot/nornir-nautobot/issues/295) - Added support for newer versions of `httpx`.
- [#297](https://github.com/nautobot/nornir-nautobot/issues/297) - Updated dependency `jsonschema` to `>=4.0.0,<5`.
- [#298](https://github.com/nautobot/nornir-nautobot/issues/298) - Updated the minimum version of `netutils` to 1.18.0.

### Documentation

- [#299](https://github.com/nautobot/nornir-nautobot/issues/299) - Fixed missing headings in the documentation.

### Housekeeping

- [#297](https://github.com/nautobot/nornir-nautobot/issues/297) - Pinned `ruff` development dependency to `^0.15.0` as v0.16 has breaking changes.
- Rebaked from the cookie `main`.
