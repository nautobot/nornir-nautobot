"""nornir dispatcher for checkpoint_gaia."""

from nornir_nautobot.plugins.tasks.dispatcher.default import NetmikoDefault


class CheckpointGaiaDefault(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to Check Point Gaia devices."""

    config_command = 'clish -c "show configuration"'
