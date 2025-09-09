
# v3.5 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

## [v3.5.0 (2025-09-09)](https://github.com/networktocode/nornir-nautobot/releases/tag/v3.5.0)

### Fixed

- [#197](https://github.com/nautobot/nornir-nautobot/issues/197) - Add the missing `netmiko_commit` to the default `merge_config` method.
- [#219](https://github.com/nautobot/nornir-nautobot/issues/219) - Fixed the `publish_gh` CI stage to properly install poetry first.
- [#223](https://github.com/nautobot/nornir-nautobot/issues/223) - Fix not passing "obj" object through to the template rendering data context.
