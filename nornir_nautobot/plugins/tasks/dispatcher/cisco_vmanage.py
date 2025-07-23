"""Netmiko dispatcher for cisco vManage controllers."""

from logging import Logger
from typing import Any

from nautobot.dcim.models import Controller, Device
from nornir.core.task import Task
from nornir_nautobot.plugins.tasks.dispatcher.base_controller_driver import (
    BaseControllerDriver,
)
from nornir_nautobot.utils.controller import (
    ConnectionMixin,
    format_base_url_with_endpoint,
    resolve_jmespath,
    resolve_query,
)
from requests import Response, Session


class NetmikoCiscoVmanage(BaseControllerDriver, ConnectionMixin):
    """Vmanage Controller Dispatcher class."""

    get_headers: dict[str, str] = {}
    post_headers: dict[str, str] = {}
    controller_url: str = ""
    session = None
    controller_type = "vmanage"

    @classmethod
    def authenticate(cls, logger: Logger, obj: Device, task: Task) -> Any:
        """Authenticate to controller.

        Args:
            logger (Logger): Logger object.
            obj (Device): Device object.
            task (Task): Nornir Task object.

        Raises:
            ValueError: Could not find the controller API URL in config context.

        Returns:
            Any: Controller object or None.
        """
        cls.session: Session = cls.configure_session()
        if controller_group := obj.controller_managed_device_group:
            controller: Controller = controller_group.controller
            cls.controller_url = controller.external_integration.remote_url
        elif controllers := obj.controllers.all():
            for cntrlr in controllers:
                if cls.controller_type in cntrlr.platform.name.lower():
                    cls.controller_url = cntrlr.external_integration.remote_url
        if not cls.controller_url:
            logger.error("Could not find the vManage URL")
            raise ValueError("Could not find the vManage URL")
        username, password = task.host.username, task.host.password
        j_security_payload = f"j_username={username}&j_password={password}"
        security_url: str = format_base_url_with_endpoint(
            base_url=cls.controller_url,
            endpoint="j_security_check",
        )
        # TODO: Change verify to true
        security_resp: Response = cls.return_response_obj(
            session=cls.session,
            method="POST",
            url=security_url,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            logger=logger,
            body=j_security_payload,
            verify=False,
        )
        j_session_id: str = security_resp.headers.get("Set-Cookie", "")
        if not j_session_id:
            logger.error(
                "Could not find JSESSIONID from vManage controller",
            )
            raise ValueError(
                "Could not find JSESSIONID from vManage controller",
            )
        token_url: str = format_base_url_with_endpoint(
            base_url=cls.controller_url,
            endpoint="dataservice/client/token",
        )
        token_resp: str = cls.return_response_content(
            session=cls.session,
            method="GET",
            url=token_url,
            headers={
                "Cookie": j_session_id,
                "Content-Type": "application/json",
            },
            verify=False,
            logger=logger,
        )
        cls.get_headers.update(
            {
                "Cookie": j_session_id,
                "Content-Type": "application/json",
                "X-XSRF-TOKEN": str(token_resp),
            }
        )

    @classmethod
    def resolve_backup_endpoint(
        cls,
        controller_obj: Any,
        logger: Logger,
        endpoint_context: list[dict[Any, Any]],
        **kwargs: Any,
    ) -> dict[str, dict[Any, Any]]:
        """Resolve endpoint with parameters if any.

        Args:
            controller_obj (Any): Controller object or None.
            logger (Logger): Logger object.
            endpoint_context (list[dict[Any, Any]]): controller endpoint context.
            kwargs (Any): Keyword arguments.

        Returns:
            Any: Dictionary of responses.
        """
        responses: dict[str, dict[Any, Any]] = {}
        for endpoint in endpoint_context:
            api_endpoint: str = format_base_url_with_endpoint(
                base_url=cls.controller_url,
                endpoint=endpoint["endpoint"],
            )
            if endpoint.get("query"):
                api_endpoint = resolve_query(
                    api_endpoint=api_endpoint,
                    query=endpoint["query"],
                )
            response = cls.return_response_content(
                session=cls.session,
                method=endpoint["method"],
                url=api_endpoint,
                headers=cls.get_headers,
                verify=False,
                logger=logger,
            )
            jpath_fields: dict[str, Any] = resolve_jmespath(
                jmespath_values=endpoint["jmespath"],
                api_response=response,
            )
            if not jpath_fields:
                logger.error(f"jmespath values not found in {response}")
                continue
            responses.update(jpath_fields)

        return responses

    # @classmethod
    # def merge_config(  # pylint: disable=too-many-positional-arguments
    #     cls,
    #     task: Task,
    #     logger,
    #     obj,
    #     config: str,
    #     can_diff: bool = True,
    # ) -> Result:
    #     """Send configuration to merge on the device.

    #     Args:
    #         task (Task): Nornir Task.
    #         logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
    #         obj (Device): A Nautobot Device Django ORM object instance.
    #         config (str): The remediation payload.
    #         can_diff (bool, optional): Can diff the config. Defaults to True.

    #     Returns:
    #         Result: Nornir Result object with a dict as a result containing what changed and the result of the push.
    #     """
    #     if isinstance(config, str):
    #         config = json.loads(config)
    #     logger.info(
    #         "Config merge via controller dispatcher starting", extra={"object": obj}
    #     )
    #     cfg_cntx: OrderedDict[Any, Any] = obj.get_config_context()
    #     # The above Python code snippet is performing the following actions:
    #     controller_obj: Any = cls.authenticate(
    #         logger=logger,
    #         obj=obj,
    #         task=task,
    #     )
    #     controller_dict: dict[str, str] = cls.controller_setup(
    #         device_obj=obj,
    #         controller_obj=controller_obj,
    #         logger=logger,
    #     )
    #     aggregated_results: list[list[dict[str, Any]]] = []
    #     feature_endpoints: str = cfg_cntx.get("remediation_endpoints", "")
    #     if not feature_endpoints:
    #         logger.error("Could not find the controller endpoints")
    #         raise ValueError("Could not find controller endpoints")
    #     for remediation_endpoint in config:
    #         if f"{remediation_endpoint}_remediation" not in feature_endpoints:
    #             logger.error(
    #                 f"Could not find the remediation endpoint: {remediation_endpoint}_remediation in {feature_endpoints}",
    #                 extra={"object": obj},
    #             )
    #             continue
    #         if not cfg_cntx.get(f"{remediation_endpoint}_remediation", ""):
    #             logger.error(
    #                 f"Could not find the remediation endpoint: {remediation_endpoint}_remediation in the config context",
    #                 extra={"object": obj},
    #             )
    #             continue
    #         try:
    #             aggregated_results.append(
    #                 cls.resolve_remediation_endpoint(
    #                     controller_obj=controller_obj,
    #                     logger=logger,
    #                     endpoint_context=cfg_cntx[
    #                         f"{remediation_endpoint}_remediation"
    #                     ],
    #                     payload=config[remediation_endpoint],
    #                     **controller_dict,
    #                 )
    #             )
    #         except NotImplementedError:
    #             logger.error("resolve_remediation_endpoint was not overriden.")
    #     if can_diff:
    #         logger.info(f"result: {aggregated_results}", extra={"object": obj})
    #         result: dict[str, Any] = {
    #             "changed": bool(aggregated_results),
    #             "result": aggregated_results,
    #             "failed": False,
    #         }
    #     else:
    #         result: dict[str, Any] = {
    #             "changed": bool(aggregated_results),
    #             "result": "Hidden to protect sensitive information",
    #             "failed": False,
    #         }

    #     logger.info("Config merge ended", extra={"object": obj})
    #     final_result: Result = Result(host=task.host, result=result)
    #     final_result.changed = True
    #     final_result.failed = False
    #     return final_result
