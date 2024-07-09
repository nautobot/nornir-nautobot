"""nornir dispatcher for Extreme EXOS."""

from nornir_nautobot.plugins.tasks.dispatcher.default import NetmikoDefault


class NetmikoExtremeEXOS(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to Extreme EXOS devices."""

    config_command = "show configuration detail"
