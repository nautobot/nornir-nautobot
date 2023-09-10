"""nornir dispatcher for Ruckus ICX/FastIron Switches."""

from nornir_nautobot.plugins.tasks.dispatcher.default import NetmikoDefault


class NetmikoRuckusFastiron(NetmikoDefault):
    """Driver for Ruckus ICX/FastIron Switches."""

    config_command = "show running-config"
