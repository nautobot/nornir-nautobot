"""Tests for the save step of the Netmiko `merge_config` dispatcher method, run through a real Nornir play.

These are the regression tests for issue #328 (https://github.com/nautobot/nornir-nautobot/issues/328), in which
each host's save ran on every host of the play, and for the related bugs found while fixing it.

Only the netmiko tasks are replaced, so `task.nornir`, `filter`, `with_processors`, the shared
`failed_hosts`, and the threaded runner are all nornir's own. Unlike the other integration tests,
these run `merge_config` across every host of the play at once, as Golden Config does for a
deployment, because a save that reaches other hosts only shows up in a multi-host, concurrent play.
"""

import threading
from collections import Counter
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
    """Stand-in for the netmiko tasks that records which host each call was made for."""

    def __init__(self):
        """Start with no recorded calls and no failures."""
        self.lock = threading.Lock()
        self.pushes = []
        self.saves = []
        self.commits = []
        self.push_errors = {}
        self.save_errors = {}
        self.commit_error = None

    def _record(self, calls, task):
        with self.lock:
            calls.append(task.host.name)

    def send_config(self, task, **kwargs):  # pylint: disable=unused-argument
        """Replace `netmiko_send_config`; raises the error set for this host, if any."""
        self._record(self.pushes, task)
        if task.host.name in self.push_errors:
            raise self.push_errors[task.host.name]
        return Result(host=task.host, result="pushed", changed=True)

    def save_config(self, task, **kwargs):  # pylint: disable=unused-argument
        """Replace `netmiko_save_config`; raises the error set for this host, if any."""
        self._record(self.saves, task)
        if task.host.name in self.save_errors:
            raise self.save_errors[task.host.name]
        return Result(host=task.host, result="saved", changed=True)

    def commit(self, task, **kwargs):  # pylint: disable=unused-argument
        """Replace `netmiko_commit`."""
        self._record(self.commits, task)
        if self.commit_error:
            raise self.commit_error
        return Result(host=task.host, result="committed", changed=True)


@pytest.fixture(name="netmiko")
def fixture_netmiko(monkeypatch):
    """Patch the netmiko tasks used by `merge_config` with recording fakes."""
    fake = FakeNetmiko()
    monkeypatch.setattr(default, "netmiko_send_config", fake.send_config)
    monkeypatch.setattr(default, "netmiko_save_config", fake.save_config)
    monkeypatch.setattr(default, "netmiko_commit", fake.commit)
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
    netmiko.commit_error = AttributeError("commit not supported")

    result = run_merge_config()

    # Only the host whose commit failed is failed.
    assert sorted(result.failed_hosts) == ["sw1"]
    # Only that host fell back to a commit; the others saved normally.
    assert netmiko.commits == ["sw1"]
    # E1016 reports the commit's error, the step that actually failed.
    assert _logged(logger.error, nornir, "sw1") == [
        "E1016: Saving Config Failed with an unknown issue: `commit not supported`"
    ]
    # No other host logged an error.
    assert _hosts_logging_errors(nornir, logger) == ["sw1"]
    # Only the hosts that really saved report a successful save.
    assert _hosts_reporting_save(nornir, logger) == ["sw2", "sw3", "sw4"]


def test_pushed_config_is_saved_on_a_host_marked_failed(nornir, netmiko, run_merge_config):
    """A host marked failed while its `merge_config` is running still has its pushed configuration saved.

    Regression test for issue #328. nornir adds hosts whose task failed to `failed_hosts`, a set shared by the
    whole play. A `.run()` call reads that set once, when it starts, to pick its hosts, and by default skips the
    marked ones; a host's task that has already started is never stopped by a later mark. Two runs are involved:

    - the outer run, Golden Config's `nr.run(run_deployment)`, picks every host at the start of the job;
    - the save, which `merge_config` starts after the push as a new `.run()`, picks its hosts again.

    A host marked between those two points was pushed but never saved. With issue #328, this happened on every
    IOS play where a save failed:

        t0  the outer run starts and picks sw1..sw4, as nothing has failed yet
        t1  sw1's configuration is pushed
        t2  sw2's save fails; the fallback commit runs on every host, fails on IOS, and marks every host failed
        t3  sw1's save starts a new run, which skips sw1 because it is now marked
        t4  sw1 raises nothing and logs "Config save ended": pushed, not saved, reported as saved

    `_save_config` now saves `task.host` even when it is marked, because the mark can also come from an earlier
    run that a caller retries with `on_failed=True`. Marking sw1 at t2 from a test would depend on thread timing,
    so the test marks it first and runs the play with `on_failed=True`, which puts sw1 in the t3 state: pushed
    while marked failed.
    """
    # Mark sw1 failed, then make the play pick it anyway, as the outer run did before the mark at t2.
    nornir.data.failed_hosts.add("sw1")

    result = run_merge_config(on_failed=True)

    # The host that was already marked failed pushed and saved successfully.
    assert not result["sw1"].failed
    # The save really ran on it: sw1 is saved once, like every other host.
    assert Counter(netmiko.saves) == {name: 1 for name in HOSTS}


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
