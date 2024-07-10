"""nornir dispatcher for checkpoint_gaia."""
from nornir.core.task import Result, Task

from nornir_nautobot.plugins.tasks.dispatcher.default import NapalmDefault, NetmikoDefault
from nornir_nautobot.exceptions import NornirNautobotException

NETMIKO_DEVICE_TYPE = "linux"


class NapalmCheckpointGaia(NapalmDefault):
    """Collection of Napalm Nornir Tasks specific to Check Point Gaia devices."""


class NetmikoCheckpointGaia(NetmikoDefault):
    """Collection of Netmiko Nornir Tasks specific to Check Point Gaia devices."""

    config_command = 'clish -c "show configuration"'

    @classmethod
    def get_config(  # pylint: disable=R0913,R0914
        cls, task: Task, logger, obj, backup_file: str, remove_lines: list, substitute_lines: list
    ) -> Result:
        """Get the latest configuration from the device.

        Args:
            task (Task): Nornir Task.
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            backup_file (str): The file location of where the back configuration should be saved.
            remove_lines (list): A list of regex lines to remove configurations.
            substitute_lines (list): A list of dictionaries with to remove and replace lines.

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        try:
            task.host.platform = NETMIKO_DEVICE_TYPE
            result = super().get_config(
                task,
                logger,
                obj,
                backup_file,
                remove_lines,
                substitute_lines,
            )
            return result
        except Exception as exc:
            error_msg = f"Failed to get configuration from {task.host.name} on {task.host.platform}"
            raise NornirNautobotException(error_msg) from exc
