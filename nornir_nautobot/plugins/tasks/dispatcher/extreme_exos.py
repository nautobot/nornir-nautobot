"""nornir dispatcher for Extreme EXOS."""

from nornir_nautobot.plugins.tasks.dispatcher.default import (
    NapalmDefault,
    NetmikoDefault,
)


class NapalmExtremeEXOS(NapalmDefault):
    """Collection of Napalm Nornir Tasks specific to ExtremeEXOS devices."""


class NetmikoExtremeEXOS(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to Extreme EXOS devices."""

    config_command = "show configuration detail"
