"""network_importer driver for arista_eos."""

from .default import NautobotNornirDriver as DefaultNautobotNornirDriver


class NautobotNornirDriver(DefaultNautobotNornirDriver):
    """Collection of Nornir Tasks specific to Arista EOS devices."""

    config_command = "show run"
