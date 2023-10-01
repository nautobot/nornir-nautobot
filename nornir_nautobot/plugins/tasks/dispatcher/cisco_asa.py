"""nornir dispatcher for cisco_asa."""

from nornir_nautobot.plugins.tasks.dispatcher.default import NapalmDefault, NetmikoDefault


class NapalmCiscoAsa(NapalmDefault):
    """Collection of Napalm Nornir Tasks specific to Cisco ASA devices."""


class NetmikoCiscoAsa(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to Cisco ASA devices."""

    config_command = "show run"
