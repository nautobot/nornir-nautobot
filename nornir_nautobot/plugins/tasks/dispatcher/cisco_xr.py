"""nornir dispatcher for cisco XR."""

from nornir_nautobot.plugins.tasks.dispatcher.default import NapalmDefault, NetmikoDefault


class NapalmCiscoXr(NapalmDefault):
    """Collection of Napalm Nornir Tasks specific to Cisco XR devices."""


class NetmikoCiscoXr(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to Cisco XR devices."""

    config_command = "show run"
