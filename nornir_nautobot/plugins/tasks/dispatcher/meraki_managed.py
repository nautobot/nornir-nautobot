"""API dispatcher for Meraki managed devices."""

from nornir_nautobot.plugins.tasks.dispatcher.cisco_meraki import (
    ApiCiscoMeraki,
)


class ApiMerakiManaged(ApiCiscoMeraki):
    """Meraki managed dispatcher class."""
