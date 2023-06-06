"""network_importer driver for cisco_asa."""

from .default import NetmikoNautobotNornirDriver as DefaultNautobotNornirDriver


class NautobotNornirDriver(DefaultNautobotNornirDriver):
    """Driver for Cisco ASA."""

    config_command = "show run"
