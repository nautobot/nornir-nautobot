"""nornir dispatcher for Juniper Junos."""

from nornir_nautobot.plugins.tasks.dispatcher.default import NapalmDefault, NetmikoDefault


class NapalmJuniperJunos(NapalmDefault):
    """Collection of Napalm Nornir Tasks specific to Juniper JUNOS devices."""


class NetmikoJuniperJunos(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to Juniper JUNOS devices."""

    config_command = "show configuration | display set"
