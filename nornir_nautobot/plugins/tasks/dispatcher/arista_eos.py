"""nornir dispatcher for arista_eos."""

from nornir_nautobot.plugins.tasks.dispatcher.default import NapalmDefault, NetmikoDefault


class NapalmAristaEos(NapalmDefault):
    """Collection of Napalm Nornir Tasks specific to Arista EOS devices."""


class NetmikoAristaEos(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to Arista EOS devices."""

    bypass_commands = r"(^\s*action bash\s*$)|(^banner .*$)"
