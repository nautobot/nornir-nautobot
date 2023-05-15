"""network_importer driver for cisco NXOS."""

from .default import NetmikoNautobotNornirDriver as DefaultNautobotNornirDriver


class NautobotNornirDriver(DefaultNautobotNornirDriver):
    """Driver for Cisco NXOS."""

    config_command = "show run"
