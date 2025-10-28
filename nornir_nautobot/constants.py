"""Holds constants for the Nornir Nautobot."""

from collections import namedtuple
from textwrap import dedent

from netmiko import NetmikoAuthenticationException, NetmikoTimeoutException

ErrorCode = namedtuple("ErrorCode", ["troubleshooting", "description", "error_message", "recommendation"])

JINJA_ERRORS = dedent("""\
    Error rendering template `{template}` at `{filename}:{line_number}`\n
    Line:\n
    ```
    {template_line}
    ```\n
    Error Type: `{error_type}`\n
    Message: `{message}`\n
""")

ERROR_CODES = {
    "E1XXX": ErrorCode(
        troubleshooting="Find the error code in the traceback, and search for it in the codebase.",
        description="This means a code snippet was calling get_error_code() with an error code that is not registered.",
        error_message="Un-Registered Error Code used.",
        recommendation="Add the error code to the constants.py file.",
    ),
    "E1000": ErrorCode(
        troubleshooting="Ensure that a valid Nautobot Device object is being passed to the dispatcher.",
        description="No Nautobot Device object was found to pass to the dispatcher.",
        error_message="No Nautobot Device object was pass to dispatcher task.",
        recommendation="Ensure that a valid Nautobot Device object is being passed to the dispatcher.",
    ),
    "E1001": ErrorCode(
        troubleshooting="Ensure that the dispatcher path is correct and that the dispatcher is installed in both the web server and worker.",
        description="A dispatcher of `{checked_path}` was provided but not found.",
        error_message="Did not find a valid dispatcher in `{checked_path}`, preemptively failed.",
        recommendation=dedent("""\
        - Check that the dispatcher path is correctly spelled and that the dispatcher is installed in both the web server and worker.
        - Manually go into `nautobot-server nbshell` and attempt the import manually."""),
    ),
    "E1002": ErrorCode(
        troubleshooting="The dispatcher provided does not have the method `{method}`, if your system administrator has not installed the dispatcher please contact them to ensure this method is provided. If the method is not provided, please use a different dispatcher, and see `https://docs.nautobot.com/projects/nornir-nautobot/en/latest/user/task/#dispatcher-sender` for more details.",
        description="Dispatcher `{driver_class}` does not have the method `{method}`.",
        error_message="Unable to locate the method `{method}` for `{driver_class}`, preemptively failed.",
        recommendation="Contact your system administrator to ensure the dispatcher is installed and the method is provided, or use a different dispatcher.",
    ),
    "E1003": ErrorCode(
        troubleshooting="Ensure that the hostname is correct and that it is reachable from the worker and web server.",
        description="The hostname `{hostname}` did not have an IP nor was resolvable.",
        error_message="The hostname `{hostname}` did not have an IP nor was resolvable, preemptively failed.",
        recommendation=dedent("""\
        - Check the hostname and ensure it is reachable from the worker and web server.
        - Make sure your systems DNS configuration is accurate in order to resolve FQDNs."""),
    ),
    "E1004": ErrorCode(
        troubleshooting="Ensure that the IP address and port are correct and that the device is reachable from the worker and web server.",
        description="Could not connect to IP: `{ip_addr}` and port: `{port}`, preemptively failed.",
        error_message="Could not connect to IP: `{ip_addr}` and port: `{port}`, preemptively failed.",
        recommendation="Check the IP address and port and ensure the device is reachable.",
    ),
    "E1005": ErrorCode(
        troubleshooting="Ensure that the username is defined and accessible for the device `{hostname}`.",
        description="There was no username defined, preemptively failed on device `{hostname}`.",
        error_message="There was no username defined, preemptively failed on device `{hostname}`.",
        recommendation="Likely the credentials class is not setup correctly, check configuration here: https://docs.nautobot.com/projects/plugin-nornir/en/latest/user/app_feature_credentials/.",
    ),
    "E1006": ErrorCode(
        troubleshooting="Ensure that the password is defined and accessible for the device `{hostname}`.",
        description="There was no password defined, preemptively failed on device `{hostname}`.",
        error_message="There was no password defined, preemptively failed on device `{hostname}`.",
        recommendation="Likely the credentials class is not setup correctly, check configuration here: https://docs.nautobot.com/projects/plugin-nornir/en/latest/user/app_feature_credentials/.",
    ),
    "E1007": ErrorCode(
        troubleshooting="Ensure that the backup file exists and is accessible.",
        description="Backup file Not Found at location: `{backup_file}`, preemptively failed.",
        error_message="Backup file Not Found at location: `{backup_file}`, preemptively failed.",
        recommendation="Likely need to ensure that the backup has been created, or that the file path is correct.",
    ),
    "E1008": ErrorCode(
        troubleshooting="Ensure that the intended config file exists and is accessible.",
        description="Intended config file NOT Found at location: `{intended_file}`, preemptively failed.",
        error_message="Intended config file NOT Found at location: `{intended_file}`, preemptively failed.",
        recommendation="Likely need to ensure that the intended config has been created, or that the file path is correct.",
    ),
    "E1009": ErrorCode(
        troubleshooting="General failure, ideally the error message for more details as it was re-raised.",
        description="General failure, ideally the error message for more details as it was re-raised.",
        error_message="UNKNOWN Failure of: {error}",
        recommendation="General failure, ideally the error message for more details as it was re-raised.",
    ),
    "E1010": ErrorCode(
        troubleshooting="Ensure that the variable is defined in the context as it is expected to be used in the Jinja2 template.",
        description="Undefined variable in Jinja2 template.",
        error_message=JINJA_ERRORS,
        recommendation="Look at the graphql query and ensure that the variable is defined in the context as it is expected to be used in the Jinja2 template.",
    ),
    "E1011": ErrorCode(
        troubleshooting="Ensure that the Jinja2 template is valid.",
        description="Syntax error in Jinja2 template.",
        error_message=JINJA_ERRORS,
        recommendation="Jinja2 template syntax error, check the template for syntax issues. Nautobot provides a Jinja2 live viewer that can be used to validate templates before use.",
    ),
    "E1012": ErrorCode(
        troubleshooting="Ensure that the Jinja2 template file exists and is accessible.",
        description="Jinja2 template file not found.",
        error_message=JINJA_ERRORS,
        recommendation=dedent("""\
            Ensure that the Jinja2 template file exists and is accessible, this is generally as an include from one template to another. Common issues include:

            - Using incorrect relative paths from the file versus absolute paths from the root templates directory
            - Incorrect file paths due to misspelling or wrong case
            - File not included on this branch
            - Permissions issues
            """),
    ),
    "E1013": ErrorCode(
        troubleshooting="Ensure that the Jinja2 template is valid, see error message for more details.",
        description="General Jinja2 template error.",
        error_message=JINJA_ERRORS,
        recommendation="Ensure that the Jinja2 template is valid, see error message for more details.",
    ),
    "E1014": ErrorCode(
        troubleshooting="Evaluate the exception message and take action as needed.",
        description="Catch all for unexpected issues of the referenced method.",
        error_message="Unknown error - `{exc.result.exception}`\n```\n{stack_trace}\n```",
        recommendation="Evaluate the exception message and take action as needed.",
    ),
    "E1015": ErrorCode(
        troubleshooting="Evaluate the exception message and take action as needed.",
        description="Catch all for unexpected issues of the referenced method.",
        error_message="The method {method} failed with an unexpected issue: `{exc.result.exception}`",
        recommendation="Evaluate the exception message and take action as needed.",
    ),
    "E1016": ErrorCode(
        troubleshooting="Review the exception message for more details.",
        description="Review the exception message for more details.",
        error_message="Saving Config Failed with an unknown issue: `{exc.result.exception}`",
        recommendation="The method `config_saved` failed with an unexpected issue: `{exc.result.exception}`",
    ),
    "E1017": ErrorCode(
        troubleshooting="Coming soon....",
        description="Coming soon....",
        error_message="Failed with an authentication issue: `{exc.result.exception}`",
        recommendation="Coming soon....",
    ),
    "E1018": ErrorCode(
        troubleshooting="Standard network troubleshooting steps apply.",
        description="Failed with a timeout issue. `{exc.result.exception}`",
        error_message="Failed with a timeout issue. `{exc.result.exception}`",
        recommendation=dedent("""\
        Validated the following:

        - Ensure the IP and hostname are correct and reachable from the worker and web server.
        - The device is accessible and not overloaded or down.
        - If the device is "slow", potentially adjust the connection_options, as shown in the docs: https://docs.nautobot.com/projects/plugin-nornir/en/latest/user/app_feature_inventory/.
        """),
    ),
    "E1019": ErrorCode(
        troubleshooting="This messages has come from the vendor. Check the worker logs for which exact command was ran.",
        description="The vendor returned a message that the command that was sent was not valid on the system.",
        error_message="Discovered `% Invalid input detected at` in the output",
        recommendation="Review the command that was sent to the device, and ensure it is valid for the device. This is generally seen on Cisco devices, but can be seen on others as well.",
    ),
    "E1020": ErrorCode(
        troubleshooting="There is a dependency that is not installed in this environment as described in the error message.",
        description="The `{dependency}` is not installed in this environment.",
        error_message="The `{dependency}` is not installed in this environment.",
        recommendation="Ensure that the required dependency is installed in the Nautobot web server and worker.",
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
        troubleshooting="This messages has come from the vendor. Check the worker logs for which exact command was ran.",
        description="The vendor returned a message that the command that was sent was not valid on the system.",
        error_message="Discovered `% Ambiguous command` in the output",
        recommendation="Review the command that was sent to the device, and ensure it is valid for the device. This is generally seen on Cisco devices, but can be seen on others as well.",
    ),
    "E1030": ErrorCode(
        troubleshooting="This is generally seen on Cisco NXOS devices. Ensure user is allowed to run the command that is being requested.",
        description="Common permission issue, primarily (and potentially exclusively) seen on Cisco NXOS.",
        error_message="Discovered `% Permission denied for the role` in the output",
        recommendation="Ensure that the actual command that is ran, is allowed for the user making the connection. As an example, if `show run` is allowed, but `show running-config` is not, would need to address that.",
    ),
    "E1031": ErrorCode(
        troubleshooting="Verify that the file for the command `{command}` exists and is accessible in the expected Git path. Check for permission issues or problems with the Git working tree.",
        description="While using offline command outputs through Git, the output file for the command `{command}` could not be retrieved due to a loading or access issue.",
        error_message="The command output file for `{command}` could not be retrieved.",
        recommendation="Ensure the file exists, the Git repository is properly cloned, and there are no permission or access issues.",
    ),
    "E1032": ErrorCode(
        troubleshooting="Verify that the output file for the command `{command}` has been generated and committed to the Git repository.",
        description="While using offline command outputs through Git, the output file for the command `{command}` was not found in the expected path.",
        error_message="The command output file for `{command}` could not be found.",
        recommendation="Ensure the command has been run and its output file has been properly stored in Git under the expected path.",
    ),
    "E1033": ErrorCode(
        troubleshooting="Verify that that command `{command}` is valid for this device.",
        description="While using the command `{command}`, return no configuration or an empty output.",
        error_message="The command output for `{command}` was empty.",
        recommendation="Review possibilites to override command sent in the docs `https://docs.nautobot.com/projects/nornir-nautobot/en/latest/user/task/#netmiko-show-running-config-command`.",
    ),
    "E1034": ErrorCode(
        troubleshooting="Verify the name and availability of any custom Jinja2 filters used in the template.",
        description="Reference to a Jinja2 filter that is not available in the environment.",
        error_message=JINJA_ERRORS,
        recommendation="Use a valid jinja filter, common reasons this error occurs include typos or jinja filter is not loaded into the Nautobot worker or web server.",
    ),
    "E1035": ErrorCode(
        troubleshooting="Verify that the username and password are correct.",
        description="The authentication credentials were not accepted.",
        error_message="Discovered `% Authentication failed` in the output",
        recommendation="Ensure that the username and password are correct.",
    ),
    "E1036": ErrorCode(
        troubleshooting="Verify that all expected prompts are defined in the prompts dictionary.",
        description="A prompt was encountered that was not defined in the prompts dictionary.",
        error_message="No prompt matched for ```\n{last_output}\n```",
        recommendation="Verify that all expected prompts are defined in the prompts dictionary.",
    ),
}

EXCEPTION_TO_ERROR_MAPPER = {
    NetmikoAuthenticationException: "E1017",
    NetmikoTimeoutException: "E1018",
    OSError: "E1031",
}
