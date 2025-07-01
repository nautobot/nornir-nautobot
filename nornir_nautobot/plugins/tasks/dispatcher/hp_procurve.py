"""nornir dispatcher for hp_procurve devices."""

from nornir_nautobot.plugins.tasks.dispatcher.default import NetmikoDefault


class HPProcurveDefault(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to HP Procurve devices."""

    config_command = "show running-config"
