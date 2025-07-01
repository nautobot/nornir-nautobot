"""nornir dispatcher for hp_comware devices."""

from nornir_nautobot.plugins.tasks.dispatcher.default import NetmikoDefault


class HPComwareDefault(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to HPE Comware 5/7 devices."""

    config_command = "display current-configuration"
