# Migrating from v4 to v5

The v4 to v5 major release boundary was triggered by the change to Scrapli as a dependency.  Going from a required dependency to an optional dependency.

## Installation Changes

Starting in 5.0, scrapli and nornir-scrapli are no longer installed by default, so if you use the scrapli framework, change your install from `pip install nornir-nautobot` to `pip install "nornir-nautobot[scrapli]"` (or, with Poetry, `poetry add nornir-nautobot -E scrapli`) everywhere you install it, including requirements files, Dockerfiles and CI.
