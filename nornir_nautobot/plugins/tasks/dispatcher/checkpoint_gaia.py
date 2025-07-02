"""nornir dispatcher for checkpoint_gaia."""

from nornir_nautobot.plugins.tasks.dispatcher.default import NapalmDefault, NetmikoDefault


class NapalmCheckpointGaia(NapalmDefault):
    """Collection of Napalm Nornir Tasks specific to Check Point Gaia devices."""

class NetmikoCheckpointGaia(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to Check Point Gaia devices."""

    config_command = '/usr/bin/clish -c "show configuration"'
