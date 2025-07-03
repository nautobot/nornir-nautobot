"""nornir dispatcher for Meraki managed devices."""

from netscaler_ext.plugins.tasks.dispatcher.cisco_meraki import NetmikoCiscoMeraki


class NetmikoMerakiManaged(NetmikoCiscoMeraki):
    """Meraki managed dispatcher class."""
