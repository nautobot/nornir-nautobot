"""network_importer driver for cisco IOS."""

from .default import NetmikoNautobotNornirDriver as DefaultNautobotNornirDriver


class NautobotNornirDriver(DefaultNautobotNornirDriver):
    """Driver for Cisco IOS."""

    config_command = "show run"
