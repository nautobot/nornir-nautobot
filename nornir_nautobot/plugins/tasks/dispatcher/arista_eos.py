"""nornir dispatcher for arista_eos."""

from nornir_nautobot.plugins.tasks.dispatcher.default import NapalmDefault, NetmikoDefault


class NapalmAristaEos(NapalmDefault):
    """Collection of Napalm Nornir Tasks specific to Arista EOS devices."""


class NetmikoAristaEos(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to Arista EOS devices."""

    config_command = "show run"
