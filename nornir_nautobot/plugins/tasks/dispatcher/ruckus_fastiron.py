"""network_importer driver for Ruckus ICX/FastIron Switches."""

from .default import NetmikoNautobotNornirDriver as DefaultNautobotNornirDriver


class NautobotNornirDriver(DefaultNautobotNornirDriver):
    """Driver for Ruckus ICX/FastIron Switches."""

    config_command = "show running-config"
