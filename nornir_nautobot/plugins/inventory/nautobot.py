"""Nornir Nautobot Inventory Plugin."""

# Python Imports
import ipaddress
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Union

# Other third party imports
import pynautobot

# Nornir Imports
from nornir.core.inventory import (
    ConnectionOptions,
    Defaults,
    Groups,
    Host,
    Hosts,
    Inventory,
)
from requests import Session

# Create Logger
logger = logging.getLogger(__name__)


QueryFilters = Union[Dict[str, Any], None]


def _normalize_query_filters(filters: QueryFilters) -> Optional[Dict[str, List[Any]]]:
    """Normalize query filters into a dict-of-lists.

    The Nautobot API (via pynautobot) accepts either scalar values or lists of values.
    This plugin normalizes to a dict-of-lists to keep merge semantics consistent.

    Examples:
        - {} or None: no filtering
        - {"name": "name one"}: single filter value
        - {"name": ["name one", "name two"]}: multiple values for same key

    Returns:
        dict or None: A dict of query params where each value is a list, or None when empty.

    Raises:
        TypeError: If filters are not a dict.
    """
    if filters is None or filters == {}:
        return None

    if not isinstance(filters, dict):
        raise TypeError("query_filters must be a dict")

    normalized: Dict[str, List[Any]] = {}
    for key, value in filters.items():
        if isinstance(value, list):
            normalized[key] = value
        else:
            normalized[key] = [value]

    return normalized or None


def _merge_query_filters(
    base: Optional[Dict[str, List[Any]]],
    extra: Optional[Dict[str, List[Any]]],
) -> Optional[Dict[str, List[Any]]]:
    """Merge two dict-of-lists filter dicts.

    When a key exists in both dicts, values are concatenated.
    """
    if base is None and extra is None:
        return None
    if base is None:
        return extra or None
    if extra is None:
        return base or None

    merged: Dict[str, List[Any]] = {}
    for key, value in base.items():
        if not isinstance(value, list):
            raise TypeError(
                f"query_filters must be a dict of lists; key '{key}' must be a list (got {type(value).__name__})"
            )
        merged[key] = list(value)

    for key, value in extra.items():
        if not isinstance(value, list):
            raise TypeError(
                f"query_filters must be a dict of lists; key '{key}' must be a list (got {type(value).__name__})"
            )

        if key in merged:
            merged[key].extend(value)
        else:
            merged[key] = list(value)

    return merged or None


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


def _add_host_to_inventory(
    hosts: Hosts,
    defaults: Defaults,
    nautobot_object,
    *,
    is_virtual: bool,
    pynautobot_dict: Union[bool, None],
):
    host: Dict[Any, Any] = {"data": {}}

    # Assign the pynautobot host object to the data key
    host["data"]["pynautobot_object"] = nautobot_object
    host["data"]["is_virtual"] = is_virtual

    # Create dictionary object available for filtering
    if pynautobot_dict:
        host["data"]["pynautobot_dictionary"] = dict(nautobot_object)

    # Add primary IP address if found
    # Otherwise use object name as hostname
    host["hostname"] = (
        str(ipaddress.IPv4Interface(nautobot_object.primary_ip4.address).ip)
        if nautobot_object["primary_ip4"]
        else (
            str(ipaddress.IPv6Interface(nautobot_object.primary_ip6.address).ip)
            if nautobot_object["primary_ip6"]
            else nautobot_object["name"]
        )
    )
    host["name"] = nautobot_object.name or str(nautobot_object.id)
    host["groups"] = []

    inventory_key = nautobot_object.name or str(nautobot_object.id)
    # TODO: Devices and VMs can share names; this overwrites (Ansible-like behavior)
    hosts[inventory_key] = _set_host(  # pylint: disable=unsupported-assignment-operation
        data=host["data"],
        name=host["name"],
        groups=host["groups"],
        host=host,
        defaults=defaults,
    )


# Setup connection to Nautobot
class NautobotInventory:  # pylint: disable=R0902
    """Nautobot Nornir Inventory."""

    def __init__(  # pylint: disable=R0913,too-many-positional-arguments
        self,
        nautobot_url: Union[str, None],
        nautobot_token: Union[str, None],
        ssl_verify: Union[bool, None] = True,
        filter_parameters: Union[Dict[str, Any], None] = None,
        pynautobot_dict: Union[bool, None] = True,
        enable_threading: Union[bool, None] = False,
        query_filters: QueryFilters = None,
        device_query_filters: QueryFilters = None,
        vm_query_filters: QueryFilters = None,
    ) -> None:
        """Nautobot nornir class initialization."""
        self.nautobot_url = nautobot_url or os.getenv("NAUTOBOT_URL")
        self.nautobot_token = nautobot_token or os.getenv("NAUTOBOT_TOKEN")

        # Legacy device-only filters
        self.filter_parameters = filter_parameters

        # New filtering model
        self.query_filters = query_filters
        self.device_query_filters = device_query_filters
        self.vm_query_filters = vm_query_filters

        self.ssl_verify = ssl_verify
        self.pynautobot_dict = pynautobot_dict
        self.enable_threading = enable_threading
        self._verify_required()
        self._api_session = None
        self._devices = None
        self._virtual_machines = None
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

    def _query_filters_for_devices(self) -> Optional[Dict[str, Any]]:
        shared = _normalize_query_filters(self.query_filters)
        legacy_device_only = _normalize_query_filters(self.filter_parameters)
        explicit_device_only = _normalize_query_filters(self.device_query_filters)

        merged = _merge_query_filters(shared, legacy_device_only)
        return _merge_query_filters(merged, explicit_device_only)

    def _query_filters_for_virtual_machines(self) -> Optional[Dict[str, Any]]:
        shared = _normalize_query_filters(self.query_filters)
        vm_only = _normalize_query_filters(self.vm_query_filters)
        return _merge_query_filters(shared, vm_only)

    @property
    def devices(self) -> list:
        """Devices information from Nautobot."""
        if self._devices is None:
            filters = self._query_filters_for_devices()
            # Cannot pass an empty dictionary to the filter method
            if filters is None:
                self._devices = self.pynautobot_obj.dcim.devices.all()
            else:
                try:
                    self._devices = self.pynautobot_obj.dcim.devices.filter(**filters)
                except pynautobot.core.query.RequestError as err:
                    print(f"Error in the query filters: {err.error}. Please verify the parameters.")
                    sys.exit(1)

        return self._devices

    @property
    def virtual_machines(self) -> list:
        """Virtual Machines information from Nautobot."""
        if self._virtual_machines is None:
            # Backwards compatibility, filter_parameters applies to Devices only
            # Do not include VMs unless VM/both filters are set
            if self.filter_parameters is not None and self.query_filters is None and self.vm_query_filters is None:
                self._virtual_machines = []
                return self._virtual_machines

            filters = self._query_filters_for_virtual_machines()
            if filters is None:
                self._virtual_machines = self.pynautobot_obj.virtualization.virtual_machines.all()
            else:
                try:
                    self._virtual_machines = self.pynautobot_obj.virtualization.virtual_machines.filter(**filters)
                except pynautobot.core.query.RequestError as err:
                    print(f"Error in the query filters: {err.error}. Please verify the parameters.")
                    sys.exit(1)

        return self._virtual_machines

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
            _add_host_to_inventory(hosts, defaults, device, is_virtual=False, pynautobot_dict=self.pynautobot_dict)

        for virtual_machine in self.virtual_machines:
            _add_host_to_inventory(
                hosts,
                defaults,
                virtual_machine,
                is_virtual=True,
                pynautobot_dict=self.pynautobot_dict,
            )

        return Inventory(hosts=hosts, groups=groups, defaults=defaults)
