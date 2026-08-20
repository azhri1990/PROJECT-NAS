import pytest

from runtime.bob_learning import LearningLedger
from runtime.bob_supervisor import PersistentSupervisor
from runtime.bob_watchdog import BoundedWatchdog


def test_healthy_worker_is_not_restarted(tmp_path):
    supervisor = PersistentSupervisor("pc-1", tmp_path / "state.json")
    supervisor.heartbeat(now=100.0)
    watchdog = BoundedWatchdog(supervisor)
    called = []

    decision = watchdog.act(now=120.0, restart=lambda: called.append(True))

    assert decision.action == "continue"
    assert called == []


def test_timeout_allows_one_bounded_restart(tmp_path):
    supervisor = PersistentSupervisor("pc-1", tmp_path / "state.json")
    supervisor.heartbeat(now=100.0)
    watchdog = BoundedWatchdog(supervisor, max_restarts=1, cooldown_seconds=0)
    called = []

    decision = watchdog.act(now=200.0, restart=lambda: called.append(True))

    assert decision.action == "restarted"
    assert called == [True]
    assert supervisor.state.restart_count == 1
    assert supervisor.state.status == "ready"


def test_restart_budget_exhaustion_escalates(tmp_path):
    supervisor = PersistentSupervisor("pc-1", tmp_path / "state.json")
    supervisor.heartbeat(now=100.0)
    watchdog = BoundedWatchdog(supervisor, max_restarts=0)

    decision = watchdog.inspect(now=200.0)

    assert decision.action == "escalate"
    assert decision.restart_allowed is False


def test_restart_cooldown_prevents_retry_storm(tmp_path):
    supervisor = PersistentSupervisor("pc-1", tmp_path / "state.json")
    supervisor.heartbeat(now=100.0)
    watchdog = BoundedWatchdog(supervisor, max_restarts=3, cooldown_seconds=60)

    assert watchdog.act(now=200.0, restart=lambda: None).action == "restarted"
    decision = watchdog.inspect(now=220.0)

    assert decision.action == "wait"
    assert decision.restart_allowed is False


def test_restart_failure_records_lesson_and_escalates_repeat(tmp_path):
    supervisor = PersistentSupervisor("pc-1", tmp_path / "state.json")
    supervisor.heartbeat(now=100.0)
    ledger = LearningLedger(tmp_path / "learning.json")
    watchdog = BoundedWatchdog(
        supervisor,
        max_restarts=3,
        cooldown_seconds=0,
        learning=ledger,
    )

    def fail():
        raise RuntimeError("crash")

    first = watchdog.act(now=200.0, restart=fail)
    second = watchdog.inspect(now=300.0)

    assert first.action == "escalate"
    assert second.action == "escalate"
    assert second.reason == "known_failure_class"
    assert ledger.known("heartbeat_timeout")
    assert supervisor.state.status == "offline"
    assert supervisor.state.restart_count == 1


def test_stopped_supervisor_is_terminal(tmp_path):
    supervisor = PersistentSupervisor("pc-1", tmp_path / "state.json")
    supervisor.start()
    supervisor.stop()
    watchdog = BoundedWatchdog(supervisor)

    decision = watchdog.inspect(now=200.0)

    assert decision.action == "stop"
    assert decision.restart_allowed is False


def test_invalid_configuration_is_rejected(tmp_path):
    supervisor = PersistentSupervisor("pc-1", tmp_path / "state.json")
    with pytest.raises(ValueError):
        BoundedWatchdog(supervisor, max_restarts=-1)
    with pytest.raises(ValueError):
        BoundedWatchdog(supervisor, cooldown_seconds=-1)
