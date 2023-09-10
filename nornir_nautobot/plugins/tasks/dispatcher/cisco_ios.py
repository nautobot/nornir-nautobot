"""nornir dispatcher for cisco IOS."""

from nornir_nautobot.plugins.tasks.dispatcher.default import NapalmDefault, NetmikoDefault


class NapalmCiscoIos(NapalmDefault):
    """Collection of Napalm Nornir Tasks specific to Cisco IOS devices."""


class NetmikoCiscoIos(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to Cisco IOS devices."""

    config_command = "show run"
