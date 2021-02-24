"""network_importer driver for cisco IOS-XR."""

from .default import NetmikoNautobotNornirDriver as DefaultNautobotNornirDriver


class NautobotNornirDriver(DefaultNautobotNornirDriver):
    """Driver for Cisco IOS-XR."""
