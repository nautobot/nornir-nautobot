# Changelog

## v2.6.0

- (#96) Changes backup_file to be conditional for get_config
- (#98) Adds merge_config method

## v2.5.0

- (#93) Updates Nornir-Netmiko to 1.0.0 release
- (#97) Adds Jinja Environment option to generate_config

## v2.4.0

- (#61) Be more clear on error messages by @itdependsnetworks
- (#66) Add basic typing to the methods in logger by @KalleDK
- (#75) Documentation refactor by @susanhooks
- (#77) added ICX/Fastiron Nornir Driver by @pato23arg
- (#78) Fix RTD docs build by @cmsirbu
- (#83) Adds provision_config method by @joewesch
- (#76) Mikrotik RouterOS CLI Support by @pato23arg
- (#79) Mikrotik RouterOS API support by @pato23arg
- (#85) Ruckus Smartzone WLC and Access Point Driver by @pato23arg

## New Contributors
* @KalleDK made their first contribution in https://github.com/nautobot/nornir-nautobot/pull/66
* @susanhooks made their first contribution in https://github.com/nautobot/nornir-nautobot/pull/75
* @pato23arg made their first contribution in https://github.com/nautobot/nornir-nautobot/pull/77
* @cmsirbu made their first contribution in https://github.com/nautobot/nornir-nautobot/pull/78
* @joewesch made their first contribution in https://github.com/nautobot/nornir-nautobot/pull/83

## v2.3.0

- (#67) fix pylint, tests, and drop py36 support #67

## v2.2.0

- (#41) Added jinja2 filter pass to generate config
- (#42) Added Cisco ASA mapping to default mapping

## v2.1.2

- (#40) Fix nornir inventory defaults

## v2.1.1

- (#31) Migrate from Travis-CI to GitHub Actions for CI
- (#32) Fix data population when generating configurations from the dispatcher

## v2.1.0

- (#26) Updates in poetry packaging for pre 1.0.0 dependencies in Nornir to allow all new up to 1.0.0 releases

## v2.0.3

- (#24) Change import mechanism / changes deprecated function

## v2.0.1

- (#20) Fixes inventory failure when platform is not defined for a device
## v2.0.0

- (#18) Migrates functions to new NTC netutils library, which is removing methods previously available:
  - compliance
  - make_folder
  - hostname_resolves
  - test_tcp_port
  - is_ip

## v0.1.0 - 2020-12-27

Initial release
