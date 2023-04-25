"""Schema."""
# Make this one configurable json schema vs statically coded pydantic objects ?

mikrotik_resources = [
    # rewrite this to be dynamic based on schema definition attached to the SerializedConfiguration.config_schema
    {
        "endpoint": "/interface",
        "keys": ["name", "type", "mtu", "disabled"],
        "unique": "",
        "unique_together": (),
        "compliance_rule_name": "interfaces",
    },
    {
        "endpoint": "/ip/address",
        "keys": ["address", "interface", "disabled", "comment"],
        "unique": "",
        "unique_together": (),
        "compliance_rule_name": "ip_address",
    },
    {
        "endpoint": "/system/identity",
        "keys": ["name"],
        "unique": "",
        "unique_together": (),
        "compliance_rule_name": "hostname",
    },
    {
        "endpoint": "/system/ntp/client",
        "keys": [
            "enabled",
            "primary-ntp",
            "secondary-ntp",
            "server-dns-names",
            "mode",
            "poll-interval",
            "active-server",
        ],
        "unique": "",
        "unique_together": (),
        "compliance_rule_name": "ntp",
    },
    {
        "endpoint": "/ip/dns",
        "keys": ["servers", "dynamic-servers", "use-doh-server"],
        "unique": "",
        "unique_together": (),
        "compliance_rule_name": "dns",
    },
    {
        "endpoint": "/snmp/community",
        "keys": ["id", "name", "addresses", "security", "read-access", "write-access", "default", "disabled"],
        "unique": "",
        "unique_together": (),
        "compliance_rule_name": "snmp",
    },
    {
        "endpoint": "/system/logging/action",
        "keys": [
            "id",
            "name",
            "target",
            "remote",
            "remote-port",
            "src-address",
            "bsd-syslog",
            "syslog-time-format",
            "syslog-facility",
            "syslog-severity",
            "default",
        ],
        "unique": "",
        "unique_together": (),
        "compliance_rule_name": "logging",
    },
]
