"""default network_importer API-based driver for Ruckus Smartzone WLC."""

import os
import json
import asyncio
import httpx  # pylint: disable=E0401
import requests

from netutils.config.clean import clean_config, sanitize_config

from nornir.core.task import Result, Task

from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.utils.helpers import make_folder

from nornir_nautobot.plugins.tasks.dispatcher.default import DispatcherMixin

AP_PLATFORM_LIST = ["ruckus_access_point", "ruckus-access-point"]


class ApiRuckusSmartzone(DispatcherMixin):
    """Default collection of Nornir Tasks tailored for Ruckus Smart Zone Controllers."""

    wlc_endpoints = {
        "simple_endpoints": [
            "/cluster/state",
            "/controller",
            "/system/snmpAgent",
            "/system/syslog",
            "/system/systemTime",
            "/profiles/dnsserver",
            "/apRules",
        ],
        "nested_endpoints": [
            "/apRules",
        ],
    }

    ap_endpoints = {
        "simple_endpoints": [
            "/rkszones",
            "/aps",
        ],
    }

    @classmethod
    def _get_hostname(cls, task: Task, obj=None) -> str:
        hostname = (
            obj.get_computed_field("wireless_controller")
            if task.host.platform in AP_PLATFORM_LIST
            else task.host.hostname
        )
        return hostname

    @classmethod
    def _api_auth(cls, obj, logger, session_params: tuple) -> dict:
        controller_ip, username, password = session_params
        headers = {"Accept": "application/json", "Content-Type": "application/json;charset=UTF-8"}
        api_version = "v9_1"
        base_url = f"https://{controller_ip}:8443/wsg/api/public/{api_version}"
        response = requests.post(  # nosec
            f"{base_url}/serviceTicket",
            verify=False,
            headers=headers,
            json={"username": username, "password": password},
            timeout=30,
        )
        if response.status_code == 200:
            data = response.json()
            service_ticket = data.get("serviceTicket")
        else:
            error_msg = (
                f"`E1023:` The `_api_auth` method failed with an unexpected issue: HTTP Error `{response.status_code}`"
            )
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)
        return service_ticket

    @classmethod
    def _build_urls(  # pylint: disable=too-many-arguments,too-many-locals
        cls,
        obj,
        logger,
        wlc_ip4: tuple,
        token: str,
        endpoints: dict,
        extras: dict,
    ) -> dict:
        url_dict = {}
        headers = {"Accept": "application/json", "Content-Type": "application/json;charset=UTF-8"}
        api_version = "v9_1"
        simple_endpoints = endpoints.get("simple_endpoints", [])
        nested_endpoints = endpoints.get("nested_endpoints", [])

        base_url = f"https://{wlc_ip4}:8443/wsg/api/public/{api_version}"

        for uri in endpoints.get("simple_endpoints"):
            if extras:
                url_dict[uri] = f'{base_url}{uri}/{extras.get(uri, "")}?serviceTicket={token}'
            else:
                url_dict[uri] = f"{base_url}{uri}?serviceTicket={token}"

        for uri in nested_endpoints:
            if uri in simple_endpoints:
                uri_list = []
                response = requests.get(
                    url=f"{base_url}{uri}?serviceTicket={token}", verify=False, headers=headers, timeout=30  # nosec
                )
                if response.status_code == 200:
                    item_list = response.json().get("list")
                else:
                    error_msg = f"`E1024:` The `{uri}` endpoint failed with code: HTTP Error `{response.status_code}`"
                    logger.error(error_msg, extra={"object": obj})
                    raise NornirNautobotException(error_msg)

                uri_list = [f'{uri}/{item["id"]}' for item in item_list]
                for uri_list_item in uri_list:
                    url_dict[uri_list_item] = f"{base_url}{uri_list_item}?serviceTicket={token}"
            else:
                error_msg = f"`E1025:` The `{uri}` endpoint missing in simple endpoints list, schema invalid`"
                logger.error(error_msg, extra={"object": obj})
                raise NornirNautobotException(error_msg)

        return url_dict

    @classmethod
    async def _async_get_data(cls, url_dict: dict) -> dict:
        # login use session params
        headers = {"Accept": "application/json", "Content-Type": "application/json;charset=UTF-8"}

        async with httpx.AsyncClient(verify=False) as client:  # nosec
            client.headers = headers
            coroutines = [client.get(url) for url in url_dict.values()]
            results = await asyncio.gather(*coroutines)

        api_data = {url: result.json() for url, result in zip(url_dict.keys(), results) if result.status_code == 200}

        return api_data

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
        logger.debug(f"Executing get_config for {task.host.name} on {task.host.platform}")
        _extras = {}
        if task.host.platform in AP_PLATFORM_LIST:
            _wlc_ip4 = obj.get_computed_field("wireless_controller")
            _extras["/rkszones"] = obj.get_computed_field("wireless_zone")
            _extras["/aps"] = obj.cf.get("basemac", "")
            _endpoints = cls.ap_endpoints
        else:
            _wlc_ip4 = task.host.hostname
            _endpoints = cls.wlc_endpoints

        _session_params = (_wlc_ip4, task.host.username, task.host.password)
        _token = cls._api_auth(obj, logger, _session_params)
        url_dict = cls._build_urls(obj, logger, _wlc_ip4, _token, _endpoints, _extras)
        config_data = asyncio.run(cls._async_get_data(url_dict))
        running_config = json.dumps(config_data, indent=4)

        if remove_lines:
            logger.debug("Removing lines from configuration based on `remove_lines` definition")
            running_config = clean_config(running_config, remove_lines)

        if substitute_lines:
            logger.debug("Substitute lines from configuration based on `substitute_lines` definition")
            running_config = sanitize_config(running_config, substitute_lines)

        make_folder(os.path.dirname(backup_file))

        with open(backup_file, "w", encoding="utf8") as filehandler:
            filehandler.write(running_config)
        return Result(host=task.host, result={"config": running_config})
