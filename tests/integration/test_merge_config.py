"""Tests for the save step of `NetmikoDefault.merge_config`, run through a real Nornir play.

These are the regression tests for issue #328 (https://github.com/nautobot/nornir-nautobot/issues/328), in which
each host's save ran on every host of the play, and for the related bugs found while fixing it.

Only the Netmiko push task and each host's Netmiko connection are replaced, so the shared `failed_hosts` and the
threaded runner are Nornir's own. Unlike the other integration tests, these run `merge_config` across every host of
the play at once, as Golden Config does for a deployment, because a save that reaches other hosts only shows up in a
multi-host, concurrent play.
"""

import threading
from collections import Counter
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from nornir.core import Nornir
from nornir.core.inventory import Host, Hosts, Inventory
from nornir.core.task import Result
from nornir.plugins.runners import ThreadedRunner

from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.plugins.tasks.dispatcher import default
from nornir_nautobot.plugins.tasks.dispatcher.default import NetmikoDefault

HOSTS = ["sw1", "sw2", "sw3", "sw4"]
# The configuration pushed to every host; the fake push ignores its content.
CONFIG = "interface Loopback0\n description merge_config test"


class FakeNetmiko:
    """Stand-in for netmiko that records which host each push, save and commit was made for."""

    def __init__(self):
        """Start with no recorded calls and no failures."""
        self.lock = threading.Lock()
        self.pushes = []
        self.saves = []
        self.commits = []
        self.config_mode_exits = []
        self.push_errors = {}
        self.save_errors = {}
        self.commit_error = None

    def record(self, calls, host_name):
        """Record a call made for `host_name`."""
        with self.lock:
            calls.append(host_name)

    def send_config(self, task, **kwargs):  # pylint: disable=unused-argument
        """Replace `netmiko_send_config`; raises the error set for this host, if any."""
        self.record(self.pushes, task.host.name)
        if task.host.name in self.push_errors:
            raise self.push_errors[task.host.name]
        return Result(host=task.host, result="pushed", changed=True)


class FakeConnection:
    """Stand-in for a host's Netmiko connection, which `_save_config` calls directly."""

    def __init__(self, netmiko, host_name):
        """Record calls into `netmiko` for `host_name`, starting outside configuration mode."""
        self.netmiko = netmiko
        self.host_name = host_name
        self.in_config_mode = False

    def save_config(self, **kwargs):  # pylint: disable=unused-argument
        """Replace Netmiko's `save_config()`; raises the error set for this host, if any."""
        self.netmiko.record(self.netmiko.saves, self.host_name)
        if self.host_name in self.netmiko.save_errors:
            raise self.netmiko.save_errors[self.host_name]
        return "saved"

    def commit(self, **kwargs):  # pylint: disable=unused-argument
        """Replace Netmiko's `commit()`, which enters configuration mode and stays there, as on Junos and IOS-XR."""
        self.netmiko.record(self.netmiko.commits, self.host_name)
        self.in_config_mode = True
        if self.netmiko.commit_error:
            raise self.netmiko.commit_error
        return "committed"

    def check_config_mode(self):
        """Replace Netmiko's `check_config_mode()`."""
        return self.in_config_mode

    def exit_config_mode(self):
        """Replace Netmiko's `exit_config_mode()`."""
        self.netmiko.record(self.netmiko.config_mode_exits, self.host_name)
        self.in_config_mode = False
        return "exited"


@pytest.fixture(name="netmiko")
def fixture_netmiko(monkeypatch, nornir):
    """Patch the netmiko push task with a recording fake, and give each host an open fake netmiko connection.

    The connection is already open when `merge_config` runs, as the push leaves it on the host, so
    `host.get_connection("netmiko", ...)` returns it instead of connecting to a device.
    """
    fake = FakeNetmiko()
    monkeypatch.setattr(default, "netmiko_send_config", fake.send_config)
    for name, host in nornir.inventory.hosts.items():
        host.connections["netmiko"] = SimpleNamespace(connection=FakeConnection(fake, name))
    return fake


@pytest.fixture(name="nornir")
def fixture_nornir(device_factory):
    """A play over several hosts with the threaded runner, as Golden Config builds for a deployment.

    As in Golden Config's inventory, each host carries its own Nautobot device in `data["obj"]`.
    """
    hosts = Hosts({name: Host(name=name, data={"obj": device_factory()}) for name in HOSTS})
    return Nornir(inventory=Inventory(hosts=hosts), runner=ThreadedRunner(num_workers=len(HOSTS)))


@pytest.fixture(name="logger")
def fixture_logger():
    """Mock job logger, in place of the shared stdlib logger, so the tests can check what was logged."""
    return MagicMock()


@pytest.fixture(name="run_merge_config")
def fixture_run_merge_config(nornir, logger):
    """Return a helper that runs `NetmikoDefault.merge_config` on every host in the play."""

    def merge_config(task):
        # As Golden Config's `run_deployment` does: each host passes its own device.
        return NetmikoDefault.merge_config(task, logger, obj=task.host.data["obj"], config=CONFIG)

    def _run(**kwargs):
        return nornir.run(task=merge_config, **kwargs)

    return _run


def _logged(log_method, nornir, host):
    """Return the messages `log_method` logged against the device of `host`."""
    device = nornir.inventory.hosts[host].data["obj"]
    return [call.args[0] for call in log_method.call_args_list if call.kwargs["extra"]["object"] is device]


def _hosts_reporting_save(nornir, logger):
    """Return the hosts that logged a successful save."""
    return [host for host in HOSTS if "Config save ended" in _logged(logger.info, nornir, host)]


def _hosts_logging_errors(nornir, logger):
    """Return the hosts that logged an error."""
    return [host for host in HOSTS if _logged(logger.error, nornir, host)]


def test_save_runs_only_on_the_deployed_host(netmiko, run_merge_config):
    """Each host's save runs on that host only, so a play of N hosts makes N saves.

    Regression test for issue #328, the core of the issue: the save ran on the whole play, so each of the N hosts
    saved all N hosts (N² saves), interleaving `write mem` into other hosts' pushes and opening extra connections.
    """
    result = run_merge_config()

    # Every host pushed and saved without error.
    assert not result.failed
    # One save per host; with issue #328 each host was saved once per host deployed (16 saves instead of 4).
    assert Counter(netmiko.saves) == {name: 1 for name in HOSTS}
    # A successful save never triggers the commit fallback.
    assert not netmiko.commits


def test_save_not_supported_falls_back_to_commit(nornir, netmiko, run_merge_config):
    """Platforms that commit instead of saving (Junos, IOS-XR) get one commit each and are not marked failed.

    Netmiko signals such a platform with `NotImplementedError` from `save_config()`; the failed save must be
    replaced by the commit without leaving the host failed in the play that Golden Config shares.

    Regression test for issue #328: the commit ran on the whole play, like the save, so each host committed all
    hosts.
    """
    netmiko.save_errors = {name: NotImplementedError() for name in HOSTS}

    result = run_merge_config()

    # A successful commit counts as a successful save.
    assert not result.failed
    # One commit per host, on the host being configured only.
    assert Counter(netmiko.commits) == {name: 1 for name in HOSTS}
    # Each host leaves the configuration mode that its commit entered, as `netmiko_commit` does.
    assert Counter(netmiko.config_mode_exits) == {name: 1 for name in HOSTS}
    # The save that failed as "not supported" did not mark any host as failed in the play's shared failed set.
    assert not nornir.data.failed_hosts


def test_failed_save_fails_only_that_host(nornir, netmiko, logger, run_merge_config):
    """A save that fails on one host fails that host with E1016 and leaves the other hosts untouched.

    Regression test for issue #328: a failed save fell back to a commit on every host (which on IOS fails and
    marks them all as failed), the save error was never reported, and every host still logged a successful save.
    """
    netmiko.save_errors = {"sw2": TimeoutError("save timed out")}

    result = run_merge_config()

    # Only the host whose save failed is failed.
    assert sorted(result.failed_hosts) == ["sw2"]
    # It failed with the dispatcher's own exception, as raised after logging E1016.
    assert type(result["sw2"][0].exception) is NornirNautobotException
    # Every host, the failed one included, attempted exactly one save.
    assert Counter(netmiko.saves) == {name: 1 for name in HOSTS}
    # A real save failure is not mistaken for "not supported", so no commit is attempted.
    assert not netmiko.commits
    # E1016 is logged against the failed host's device, with the original save error.
    assert _logged(logger.error, nornir, "sw2") == [
        "E1016: Saving Config Failed with an unknown issue: `save timed out`"
    ]
    # No other host logged an error.
    assert _hosts_logging_errors(nornir, logger) == ["sw2"]
    # Only the hosts that really saved report a successful save.
    assert _hosts_reporting_save(nornir, logger) == ["sw1", "sw3", "sw4"]


def test_save_attribute_error_does_not_fall_back_to_commit(nornir, netmiko, logger, run_merge_config):
    """Only `NotImplementedError` means "commit instead"; any other save error, here an `AttributeError`, is a failure.

    An `AttributeError` from a save is a real problem, such as a dropped session. Treating it as "not supported"
    would run a commit and report the commit's error instead of the save's.

    Regression test for a bug found while fixing issue #328: any failed save fell back to a commit, so a real save
    error was reported as the commit's error.
    """
    netmiko.save_errors = {"sw3": AttributeError("'NoneType' object has no attribute 'send'")}

    result = run_merge_config()

    # Only the host whose save failed is failed.
    assert sorted(result.failed_hosts) == ["sw3"]
    # The AttributeError did not trigger the commit fallback.
    assert not netmiko.commits
    # E1016 reports the save's own error, not a commit error.
    assert _logged(logger.error, nornir, "sw3") == [
        "E1016: Saving Config Failed with an unknown issue: `'NoneType' object has no attribute 'send'`"
    ]
    # No other host logged an error.
    assert _hosts_logging_errors(nornir, logger) == ["sw3"]
    # Only the hosts that really saved report a successful save.
    assert _hosts_reporting_save(nornir, logger) == ["sw1", "sw2", "sw4"]


def test_failed_commit_fails_the_host(nornir, netmiko, logger, run_merge_config):
    """When saving is not supported and the commit that replaces it fails, the host fails with the commit error.

    Regression test for issue #328: the commit ran on the whole play and its failure was never reported, so the
    host still logged a successful save.
    """
    netmiko.save_errors = {"sw1": NotImplementedError()}
    # The error Netmiko's `commit()` raises on Junos and IOS-XR when the device rejects the commit.
    netmiko.commit_error = ValueError(
        "Commit failed with the following errors:\n\nerror: configuration check-out failed"
    )

    result = run_merge_config()

    # Only the host whose commit failed is failed.
    assert sorted(result.failed_hosts) == ["sw1"]
    # Only that host fell back to a commit; the others saved normally.
    assert netmiko.commits == ["sw1"]
    # E1016 reports the commit's error, the step that actually failed.
    assert _logged(logger.error, nornir, "sw1") == [
        "E1016: Saving Config Failed with an unknown issue: "
        "`Commit failed with the following errors:\n\nerror: configuration check-out failed`"
    ]
    # No other host logged an error.
    assert _hosts_logging_errors(nornir, logger) == ["sw1"]
    # Only the hosts that really saved report a successful save.
    assert _hosts_reporting_save(nornir, logger) == ["sw2", "sw3", "sw4"]


def test_failed_push_fails_only_that_host_without_saving(nornir, netmiko, logger, run_merge_config):
    """A push that fails on one host fails that host with the dispatcher's own exception, skips its save, and
    leaves the other hosts untouched.

    Regression test for a bug found while fixing issue #328: the push error was logged but not raised, and
    `merge_config` then crashed with an `UnboundLocalError` on the missing push result.
    """
    netmiko.push_errors = {"sw2": RuntimeError("push failed")}

    result = run_merge_config()

    # Only the host whose push failed is failed.
    assert sorted(result.failed_hosts) == ["sw2"]
    # It failed with the dispatcher's own exception, not an UnboundLocalError.
    assert type(result["sw2"][0].exception) is NornirNautobotException
    # Every host, the failed one included, attempted exactly one push.
    assert Counter(netmiko.pushes) == {name: 1 for name in HOSTS}
    # No save is attempted after a failed push; the other hosts each saved once.
    assert Counter(netmiko.saves) == {"sw1": 1, "sw3": 1, "sw4": 1}
    # The push error is logged once against the failed host's device, with the original error. The full message
    # is not checked because E1016 says "Saving Config Failed" even for a failed push.
    sw2_errors = _logged(logger.error, nornir, "sw2")
    assert len(sw2_errors) == 1
    assert "push failed" in sw2_errors[0]
    # No other host logged an error.
    assert _hosts_logging_errors(nornir, logger) == ["sw2"]
    # Only the hosts that really saved report a successful save.
    assert _hosts_reporting_save(nornir, logger) == ["sw1", "sw3", "sw4"]
