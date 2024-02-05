"""Nornir Nautobot Inventory Plugin."""

# Python Imports
import os
import sys
import ipaddress
import logging
from typing import Any, Dict, Union

# Nornir Imports
from nornir.core.inventory import (
    Inventory,
    ConnectionOptions,
    Defaults,
    Groups,
    Host,
    Hosts,
)

# Other third party imports
import pynautobot
from requests import Session

# Create Logger
logger = logging.getLogger(__name__)


def _set_host(data: Dict[str, Any], name: str, groups, host, defaults: Defaults) -> Host:
    host_platform = getattr(data["pynautobot_object"].platform, "network_driver", None)
    connection_option = {}
    for key, value in data.get("connection_options", {}).items():
        connection_option[key] = ConnectionOptions(
            hostname=value.get("hostname"),
            port=value.get("port"),
            username=value.get("username"),
            password=value.get("password"),
            platform=host_platform,
            extras=value.get("extras"),
        )

    return Host(
        name=name,
        hostname=host["hostname"],
        username=host.get("username"),
        password=host.get("password"),
        platform=host_platform,
        data=data,
        groups=groups,
        defaults=defaults,
        connection_options=connection_option,
    )


# Setup connection to Nautobot
class NautobotInventory:  # pylint: disable=R0902
    """Nautobot Nornir Inventory."""

    def __init__(  # pylint: disable=R0913
        self,
        nautobot_url: Union[str, None],
        nautobot_token: Union[str, None],
        ssl_verify: Union[bool, None] = True,
        filter_parameters: Union[Dict[str, Any], None] = None,
        pynautobot_dict: Union[bool, None] = True,
        enable_threading: Union[bool, None] = False,
    ) -> None:
        """Nautobot nornir class initialization."""
        self.nautobot_url = nautobot_url or os.getenv("NAUTOBOT_URL")
        self.nautobot_token = nautobot_token or os.getenv("NAUTOBOT_TOKEN")
        self.filter_parameters = filter_parameters
        self.ssl_verify = ssl_verify
        self.pynautobot_dict = pynautobot_dict
        self.enable_threading = enable_threading
        self._verify_required()
        self._api_session = None
        self._devices = None
        self._pynautobot_obj = None

    def _verify_required(self) -> bool:
        """Verify that required parameters are provided either passed in or via environment.

        Returns:
            bool: Successful

        Raises:
            ValueError: When incorrect value is provided
        """
        for item in [self.nautobot_url, self.nautobot_token]:
            if item is None:
                raise ValueError("Missing URL or Token from parameters or environment.")

        return True

    @property
    def api_session(self):
        """Requests session to pass into Nautobot."""
        if self._api_session is None:
            self._api_session = Session()
            self._api_session.verify = self.ssl_verify

        return self._api_session

    @property
    def pynautobot_obj(self) -> pynautobot.core.api.Api:
        """Pynautobot API object to interact with Nautobot.

        Returns:
            pynautobot object: Object to interact with the pynautobot SDK.
        """
        if self._pynautobot_obj is None:
            self._pynautobot_obj = pynautobot.api(
                self.nautobot_url,
                token=self.nautobot_token,
                threading=self.enable_threading,
                verify=self.ssl_verify,
            )
            self.api_session.params = {"depth": 1}

            self._pynautobot_obj.http_session = self.api_session

        return self._pynautobot_obj

    @property
    def devices(self) -> list:
        """Devices information from Nautobot."""
        if self._devices is None:
            # Check for filters. Cannot pass an empty dictionary to the filter method
            if self.filter_parameters is None:
                self._devices = self.pynautobot_obj.dcim.devices.all()
            else:
                try:
                    self._devices = self.pynautobot_obj.dcim.devices.filter(**self.filter_parameters)
                except pynautobot.core.query.RequestError as err:
                    print(f"Error in the query filters: {err.error}. Please verify the parameters.")
                    sys.exit(1)

        return self._devices

    # Build the inventory
    def load(self) -> Inventory:
        """Load of Nornir inventory.

        Returns:
            Inventory: Nornir Inventory
        """
        hosts = Hosts()
        groups = Groups()
        defaults = Defaults()

        for device in self.devices:
            # Set the base information for a device
            host: Dict[Any, Any] = {"data": {}}

            # Assign the pynautobot host object to the data key
            host["data"]["pynautobot_object"] = device

            # Create dictionary object available for filtering
            if self.pynautobot_dict:
                host["data"]["pynautobot_dictionary"] = dict(device)
            # TODO: #3 Investigate Nornir compatability with dictionary like object

            # Add Primary IP address, if found. Otherwise add hostname as the device name
            host["hostname"] = (
                str(ipaddress.IPv4Interface(device.primary_ip4.address).ip)
                if device["primary_ip4"]
                else (
                    str(ipaddress.IPv6Interface(device.primary_ip6.address).ip)
                    if device["primary_ip6"]
                    else device["name"]
                )
            )
            host["name"] = device.name or str(device.id)
            host["groups"] = []

            # Add host to hosts by name first, ID otherwise - to string
            hosts[device.name or str(device.id)] = _set_host(  # pylint: disable=unsupported-assignment-operation
                data=host["data"],
                name=host["name"],
                groups=host["groups"],
                host=host,
                defaults=defaults,
            )

        return Inventory(hosts=hosts, groups=groups, defaults=defaults)
