"""Holds constants for the Nornir Nautobot."""

from collections import namedtuple

import jinja2
from netmiko import NetmikoAuthenticationException, NetmikoTimeoutException

ErrorCode = namedtuple("ErrorCode", ["troubleshooting", "description", "error_message", "recommendation"])

ERROR_CODES = {
    "E1XXX": ErrorCode(
        troubleshooting="Find the error code in the traceback, and search for it in the codebase.",
        description="This means a code snippet was calling get_error_code() with an error code that is not registered.",
        error_message="Un-Registered Error Code used.",
        recommendation="Add the error code to the constants.py file.",
    ),
    "E1001": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Did not find a valid dispatcher in {checked_path}, preemptively failed.",
        recommendation="Coming soon....",
    ),
    "E1002": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Unable to locate the method {method} for {driver_class}, preemptively failed.",
        recommendation="Coming soon....",
    ),
    "E1003": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="The hostname {hostname} did not have an IP nor was resolvable, preemptively failed.",
        recommendation="Coming soon....",
    ),
    "E1004": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Could not connect to IP: `{ip_addr}` and port: `{port}`, preemptively failed.",
        recommendation="Coming soon....",
    ),
    "E1005": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="There was no username defined, preemptively failed.",
        recommendation="Coming soon....",
    ),
    "E1006": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="There was no password defined, preemptively failed.",
        recommendation="Coming soon....",
    ),
    "E1007": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Backup file Not Found at location: `{backup_file}`, preemptively failed.",
        recommendation="Coming soon....",
    ),
    "E1008": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Intended config file NOT Found at location: `{intended_file}`, preemptively failed.",
        recommendation="Coming soon....",
    ),
    "E1009": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="UNKNOWN Failure of: {error}",
        recommendation="Coming soon....",
    ),
    "E1010": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Undefined variable in Jinja2 template",
        recommendation="Coming soon....",
    ),
    "E1011": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Syntax error in Jinja2 template - ``{exc.result.exception}``\n```\n{stack_trace}\n```",
        recommendation="Coming soon....",
    ),
    "E1012": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Jinja2 template not found - ``{exc.result.exception}``\n```\n{stack_trace}\n```",
        recommendation="Coming soon....",
    ),
    "E1013": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="General Jinja2 template error - ``{exc.result.exception}``\n```\n{stack_trace}\n```",
        recommendation="Coming soon....",
    ),
    "E1014": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Unknown error - `{exc.result.exception}`\n```\n{stack_trace}\n```",
        recommendation="Coming soon....",
    ),
    "E1015": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="The method {method} failed with an unexpected issue: `{exc.result.exception}`",
        recommendation="Coming soon....",
    ),
    "E1016": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Saving Config Failed with an unknown issue: `{exc.result.exception}`",
        recommendation="Coming soon....",
    ),
    "E1017": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Failed with an authentication issue: `{exc.result.exception}`",
        recommendation="Coming soon....",
    ),
    "E1018": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Failed with a timeout issue. `{exc.result.exception}`",
        recommendation="Coming soon....",
    ),
    "E1019": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Discovered `% Invalid input detected at` in the output",
        recommendation="Coming soon....",
    ),
    "E1020": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="The `{dependency}` is not installed in this environment.",
        recommendation="Coming soon....",
    ),
    "E1021": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="The method `get_config` failed with an unexpected issue: `{exc.result.exception}`",
        recommendation="Coming soon....",
    ),
    "E1022": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="The method `get_config` failed with an unexpected issue: `{exc.result.exception}`",
        recommendation="Coming soon....",
    ),
    "E1023": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="The `_api_auth` method failed with an unexpected issue: HTTP Error `{response.status_code}`",
        recommendation="Coming soon....",
    ),
    "E1024": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="The `{uri}` endpoint failed with code: HTTP Error `{response.status_code}`",
        recommendation="Coming soon....",
    ),
    "E1025": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="The `{uri}` endpoint missing in simple endpoints list, schema invalid`",
        recommendation="Coming soon....",
    ),
    "E1026": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="result: {push_result[0].result}",
        recommendation="Coming soon....",
    ),
    "E1027": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="The method `config_merged`, but failed to save: {exc.result.exception}",
        recommendation="Coming soon....",
    ),
    "E1028": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Discovered `% Incomplete command` in the output",
        recommendation="Coming soon....",
    ),
    "E1029": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Discovered `% Ambiguous command` in the output",
        recommendation="Coming soon....",
    ),
}

EXCEPTION_TO_ERROR_MAPPER = {
    NetmikoAuthenticationException: "E1017",
    NetmikoTimeoutException: "E1018",
    jinja2.exceptions.UndefinedError: "E1010",
    jinja2.TemplateSyntaxError: "E1011",
    jinja2.TemplateNotFound: "E1012",
    jinja2.TemplateError: "E1013",
}
