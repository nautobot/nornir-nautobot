"""nornir dispatcher for cisco NXOS."""

from nornir_nautobot.plugins.tasks.dispatcher.default import NapalmDefault, NetmikoDefault


class NapalmCiscoNxos(NapalmDefault):
    """Collection of Napalm Nornir Tasks specific to Cisco NXOS devices."""


class NetmikoCiscoNxos(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to Cisco NXOS devices."""

    config_command = "show run"
