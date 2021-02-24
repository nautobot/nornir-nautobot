"""Filter Plugins for compliance checks."""

from . import parser  # pylint: disable=relative-beyond-top-level

parser_map = {
    "arista_eos": parser.EOSConfigParser,
    "cisco_ios": parser.IOSConfigParser,
    "cisco_nxos": parser.NXOSConfigParser,
    "cisco_aireos": parser.AIREOSConfigParser,
    "linux": parser.LINUXConfigParser,
    "bigip_f5": parser.F5ConfigParser,
    "juniper_junos": parser.JunosConfigParser,
}

default_feature = {
    "compliant": None,
    "missing": None,
    "extra": None,
    "cannot_parse": True,
    "unordered_compliant": None,
    "ordered_compliant": None,
    "actual": None,
    "intended": None,
}

# TODO: Update doc string examples to reflect the how the functions currently work
def section_config(feature, device_cfg, network_os):
    """Parse feature section config from device cfg.

        In case section attribute of the the feature is not provided
        entire content of the device_cfg is returned.

    Args:
        feature (dict): Feature name and cfg lines that should be parsed.
        device_cfg (str): Device configuration.
        network_os (str): Device network operating system.

    Returns:
        list: The hash report data mapping file hashes to report data.

    Example:
        >>> feature
        ... {
        ...    "name": "BGP",
        ...    "section": [
        ...        "router bgp "
        ...    ]
        ... }
        >>> print(device_cfg)
        ... router bgp 100
        ...  bgp router-id 10.6.6.5
        ... !
        ... snmp-server ifindex persist
        ... snmp-server packetsize 4096
        ... snmp-server location BOMI/ITAJAI
        ... access-list 1 permit 10.22.142.132
        ... access-list 1 permit 10.22.143.189
        >>>
        >>> section_config(feature, device_cfg, "ios")
        ... router bgp 100
        ...  bgp router-id 10.6.6.5
        >>>
    """
    section_starts_with = feature.get("section")
    if not section_starts_with:
        return device_cfg

    match = False
    section_config_list = []
    os_parser = parser_map[network_os]
    config_parsed = os_parser(device_cfg)
    for line in config_parsed.config_lines:
        if match:
            if line.parents:  # pylint: disable=no-else-continue
                section_config_list.append(line.config_line)
                continue
            else:
                match = False
        for line_start in section_starts_with:
            if not match and line.config_line.startswith(line_start):
                section_config_list.append(line.config_line)
                match = True
    return "\n".join(section_config_list).strip()


def compliance(features, backup, intended, network_os):
    r"""Report compliance for all features provided as input.

    Args:
        features (list): List of features for particular network os.
        backup (path): running config or config backup file  to compare against intended.
        intended (path): intended config to compare against backup.
        network_os (str): Device network operating system.

    Returns:
        dict: Compliance information per feature.

    Example:
        >>> features
        ... [
        ...     {
        ...         "name": "hostname",
        ...         "section": [
        ...             "hostname"
        ...         ]
        ...     },
        ...     {
        ...         "name": "ntp",
        ...         "section": [
        ...             "ntp"
        ...         ]
        ...     },
        ...     {
        ...         "name": "local_users",
        ...         "section": [
        ...             "username",
        ...             "role network-limited"
        ...         ]
        ...     }
        ... ]
        >>> backup = "my/path/to/backup/file.cfg"
        >>> intended = "my/path/to/intended/config.cfg"
        >>> network_os = "aruba"
        >>> compliance(features, backup, intended, network_os)
        ... {
        ...     "hostname": {
        ...         "cannot_parse": false,
        ...         "compliant": true,
        ...         "existing": "hostname R1",
        ...         "golden": "hostname R1",
        ...         "not_required": null,
        ...         "required": null,
        ...         "unordered_compliant": null
        ...     },
        ...     "ntp": {
        ...         "cannot_parse": false,
        ...         "compliant": false,
        ...         "existing": "ntp server 192.168.1.1\nntp server 192.168.1.2 prefer",
        ...         "golden": "ntp server 192.168.1.1\nntp server 192.168.1.5 prefer",
        ...         "not_required": "ntp server 192.168.1.2 prefer",
        ...         "required": "ntp server 192.168.1.5 prefer",
        ...         "unordered_compliant": false
        ...     }
        ... }
    """
    backup_cfg = open_file_config(backup)
    intended_cfg = open_file_config(intended)

    compliance_results = dict()

    for feature in features:

        feature_compliance = default_feature.copy()
        backup_feature = section_config(feature, backup_cfg, network_os)
        intended_feature = section_config(feature, intended_cfg, network_os)

        feature_compliance["actual"] = backup_feature
        feature_compliance["intended"] = intended_feature

        feature_compliance["ordered_compliant"] = _is_feature_ordered_compliant(intended_feature, backup_feature)

        if feature_compliance["ordered_compliant"]:
            feature_compliance.update(
                {
                    "missing": "",
                    "extra": "",
                    "unordered_compliant": True,
                }
            )
        else:
            if backup_feature and intended_feature:
                feature_compliance.update(_check_configs_differences(intended_feature, backup_feature, network_os))
        if feature["ordered"] is True:
            feature_compliance["compliant"] = feature_compliance["ordered_compliant"]
        elif feature["ordered"] is False:
            feature_compliance["compliant"] = feature_compliance["unordered_compliant"]
        else:
            raise  # pylint: disable=misplaced-bare-raise
        compliance_results.update({feature["name"]: feature_compliance})
    return compliance_results


def _is_feature_ordered_compliant(feature_intended_cfg, feature_actual_cfg):
    """Check if feature intended cfg is compliant with feature actual cfg.

    Args:
        feature_intended_cfg (str): Feature intended configuration.
        feature_actual_cfg: (str): Feature actual configuration.

    Returns:
        bool

    Example:
        >>> print(feature_intended_cfg)
        ... router bgp 100
        ...  bgp router-id 10.6.6.5
        >>>
        >>> print(feature_actual_cfg)
        ... router bgp 100
        ...  bgp router-id 10.6.6.5
        >>>
        >>> print(_is_feature_compliant(feature_intended_cfg, feature_actual_cfg))
        ... True
        >>>
    """
    if not feature_intended_cfg and not feature_actual_cfg:
        return True
    if feature_intended_cfg == feature_actual_cfg:
        return True
    return False


def _check_configs_differences(intended_cfg, actual_cfg, network_os):
    r"""Find differences between intended and actual config lines.

    Args:
        intended_cfg (str): Feature intended configuration.
        actual_cfg: (str): Feature actual configuration.
        network_os (str): Device network operating system.

    Returns:
        dict: Config fragments that are missing, extra or unordered_compliant.

    Example:
        >>> print(intended_cfg)
        ... ntp server 10.10.10.10
        ... ntp server 10.10.10.11
        >>>
        >>> print(actual_cfg)
        ... ntp server 10.10.10.10
        ... ntp server 192.168.0.1
        >>>
        >>> _check_configs_differences(intended_cfg, actual_cfg, network_os)
        ... {
        ...     "missing": "ntp server 10.10.10.11",
        ...     "extra": "ntp server 192.168.0.1",
        ...     "unordered_compliant": False,
        ... }
        >>>
    """
    missing = ntc_diff_network_config(intended_cfg, actual_cfg, network_os)
    extra = ntc_diff_network_config(actual_cfg, intended_cfg, network_os)
    if not missing and not extra:
        unordered_compliant, _ = find_unordered_cfg_lines(intended_cfg, actual_cfg)
    else:
        unordered_compliant = False
    return {
        "missing": missing,
        "extra": extra,
        "unordered_compliant": unordered_compliant,
    }


def find_unordered_cfg_lines(intended_cfg, actual_cfg):
    """Check if config lines are miss-ordered, i.e in ACL-s.

    Args:
        intended_cfg (str): Feature intended configuration.
        actual_cfg: (str): Feature actual configuration.

    Returns:
        list: List of tuples with unordered_compliant cfg lines.

    Example:
        >>> print(intended_cfg)
        ... ntp server 10.10.10.10
        ... ntp server 10.10.10.11
        ... ntp server 10.10.10.12
        >>>
        >>> print(actual_cfg)
        ... ntp server 10.10.10.12
        ... ntp server 10.10.10.11
        ... ntp server 10.10.10.10
        >>>
        >>> find_unordered_compliant_cfg_lines(intended_cfg, actual_cfg)
        ... [
        ...     ("ntp server 10.10.10.10", "ntp server 10.10.10.12"),
        ...     ("ntp server 10.10.10.12", "ntp server 10.10.10.10")
        ... ]
        >>>
    """
    intended_lines = intended_cfg.splitlines()
    actual_lines = actual_cfg.splitlines()
    unordered_lines = list()
    if len(intended_lines) == len(actual_lines):
        # Process to find actual lines that are misordered
        unordered_lines = [(e1, e2) for e1, e2 in zip(intended_lines, actual_lines) if e1 != e2]
    # Process to find determine if there are any different lines, regardless of order
    if not set(intended_lines).difference(actual_lines):
        return (True, unordered_lines)
    return (False, unordered_lines)


def config_section_not_parsed(features, device_cfg, network_os):
    """Return device config section that is not checked by compliance.

    Args:
        features (list): List of features for particular network os.
        device_cfg (str): Device configuration.
        network_os (str): Device network operating system.

    Returns:
        dict: Config that was not parsed or section not found.

    Example:
        >>> features
        ... [{
        ...    "name": "BGP",
        ...    "section": [
        ...        "router bgp "
        ...    ]
        ... }]
        >>> print(device_cfg)
        ... router bgp 100
        ...  bgp router-id 10.6.6.5
        ... !
        ... access-list 1 permit 10.10.10.10
        ... access-list 1 permit 10.10.10.11
        >>>
        >>> config_section_not_parsed(features, device_cfg, network_os)
        ... {
        ...     "remaining_cfg":
        ...         "access-list 1 permit 10.10.10.10
        ...          access-list 1 permit 10.10.10.11",
        ...     "section_not_found": []
        ... }
        >>>
    """
    remaining_cfg = device_cfg
    section_not_found = list()
    for feature in features:
        feature_cfg = section_config(feature, device_cfg, network_os)
        if not feature_cfg:
            section_not_found.append(feature["name"])
        remaining_cfg = remaining_cfg.replace(feature_cfg, "")
    return {
        "remaining_cfg": remaining_cfg.strip(),
        "section_not_found": section_not_found,
    }


def open_file_config(cfg_path):
    """Open config file from local disk."""
    try:
        with open(cfg_path) as filehandler:
            device_cfg = filehandler.read()
    except IOError:
        return False
    return device_cfg.strip()


def ntc_diff_network_config(compare_config, base_config, network_os):
    """Identify which lines in compare_config are not in base_config.

    Args:
        compare_config (str): The config to evaluate against base_config.
        base_config (str): The config to compare compare_config against.
        network_os (str): The OS per ansible_network_os.

    Returns:
        base_config (str): The string of additional commands in compare_config separated by a newline.
    """
    os_parser = parser_map[network_os]
    compare_parser = os_parser(compare_config)
    base_parser = os_parser(base_config)
    base = set(base_parser.config_lines)

    needed_lines = []
    for line in compare_parser.config_lines:
        if line not in base:
            for parent in line.parents:
                if parent not in needed_lines:
                    needed_lines.append(parent)
            needed_lines.append(line.config_line)

    return "\n".join(needed_lines)
