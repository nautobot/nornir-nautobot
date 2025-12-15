"""Netmiko dispatcher for Meraki managed devices."""

from nornir_nautobot.plugins.tasks.dispatcher.cisco_meraki import (
    NetmikoCiscoMeraki,
)


class NetmikoMerakiManaged(NetmikoCiscoMeraki):
    """Meraki managed dispatcher class."""
