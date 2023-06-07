"""default network_importer driver for Juniper."""

from .default import NetmikoNautobotNornirDriver as DefaultNautobotNornirDriver


class NautobotNornirDriver(DefaultNautobotNornirDriver):
    """Collection of Nornir Tasks specific to Juniper Junos devices."""

    config_command = "show configuration | display set"
