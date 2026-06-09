"""Fixtures for dispatcher integration tests.

These build a real Nornir runner against a small static inventory and drive the
dispatcher classmethods end-to-end, so the offline path actually executes
``task.run`` -> ``get_git_command`` -> on-disk file read -> ``_parse_offline_output``.
No device connection is opened (offline reads from files), so the suite is
network-free and CI-safe.
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from nornir import InitNornir

INVENTORY_DIR = Path(__file__).parent / "inventory"
COMMAND_OUTPUTS_DIR = Path(__file__).parent / "command_outputs"


@pytest.fixture()
def nornir_runner():
    """Return a Nornir object backed by a static, connection-free inventory."""
    return InitNornir(
        runner={"plugin": "serial"},
        inventory={
            "plugin": "SimpleInventory",
            "options": {
                "host_file": str(INVENTORY_DIR / "hosts.yaml"),
                "group_file": str(INVENTORY_DIR / "groups.yaml"),
                "defaults_file": str(INVENTORY_DIR / "defaults.yaml"),
            },
        },
        logging={"enabled": False},
    )


@pytest.fixture()
def logger():
    """Return a plain Python logger; the dispatchers accept a Job or stdlib logger."""
    return logging.getLogger("nornir-nautobot-integration")


@pytest.fixture()
def command_outputs_dir():
    """Return the path to the fixture "Git repository" of stored command outputs."""
    return COMMAND_OUTPUTS_DIR


@pytest.fixture()
def device_factory():
    """Return a factory that builds a stand-in for a Nautobot Device.

    Offline reads only touch ``obj`` for error-log context and (when not forced)
    the ``offline_commands`` lookup, so a light stub is sufficient here — a real
    Device would require a live Nautobot instance.
    """

    def _make_device(custom_fields=None, config_context=None):
        obj = MagicMock()
        obj.cf = custom_fields or {}
        obj.get_config_context.return_value = config_context or {}
        return obj

    return _make_device


@pytest.fixture()
def run_dispatcher(nornir_runner):
    """Return a helper that runs a dispatcher classmethod against a single host.

    The dispatcher classmethod is already ``cls``-bound, so Nornir injects the
    real ``Task`` as the first argument and forwards the rest as keywords. The
    returned value is the host's ``MultiResult``; element ``[0]`` is the
    dispatcher method's own ``Result`` and later elements are its subtasks.
    """

    def _run(host, task, **kwargs):
        return nornir_runner.filter(name=host).run(task=task, **kwargs)[host]

    return _run
