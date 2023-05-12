"""Used to define default platform settings."""

ROUTEROS_API_ENDPOINTS = [
    "/system/identity",
    "/interface",
    "/ip/address",
    "/system/ntp/client",
    "/ip/dns",
    "/snmp/community",
    "/system/logging/action",
]

COMMAND_MAPPINGS = {
    "default": "show run",
    "cisco_nxos": "show run",
    "cisco_ios": "show run",
    "cisco_xr": "show run",
    "juniper_junos": "show configuration | display set",
    "arista_eos": "show run",
    "mikrotik_routeros": "export terse",
    "ruckus_fastiron": "show running-config",
    "mikrotik_routeros_api": ROUTEROS_API_ENDPOINTS,
}
