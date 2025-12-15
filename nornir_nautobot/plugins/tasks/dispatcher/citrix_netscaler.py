"""Netmiko dispatcher for Citrix Netscaler controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from logging import Logger

    from nornir.core.task import Task
    from requests import Session

from nornir_nautobot.plugins.tasks.dispatcher.api_base_dispatcher import (
    ApiBaseDispatcher,
)


def use_snip_hostname(hostname: str) -> str:
    """Use the SNIP hostname format for Citrix Netscaler.

    Args:
        hostname (str): The original hostname.

    Returns:
        str: The formatted SNIP hostname.
    """
    if hostname[-2:].isdigit():
        stripped_hostname: str = hostname.rsplit(maxsplit=1, sep="_")[-1]
        return stripped_hostname[:-2] + "snip.ipaper.com"
    return hostname


class NetmikoCitrixNetscaler(ApiBaseDispatcher):
    """Netscaler Controller Dispatcher class."""

    @classmethod
    def authenticate(cls, logger: Logger, obj, task: Task) -> Any:
        """Authenticate to controller.

        Args:
            logger (Logger): Logger object.
            obj (Device): Device object.
            task (Task): Nornir Task object.

        Returns:
            Any: Controller object or None.
        """
        hostname: str = use_snip_hostname(hostname=obj.name)
        cls.url: str = f"https://{hostname}"
        cls.session: Session = cls.configure_session()
        username: str = task.host.username
        password: str = task.host.password
        cls.get_headers = {
            "X-NITRO-USER": username,
            "X-NITRO-PASS": password,
            "Content-Type": "application/json",
        }
