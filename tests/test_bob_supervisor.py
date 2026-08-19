import json

import pytest

from runtime.bob_supervisor import PersistentSupervisor


def test_state_survives_restart(tmp_path):
    path = tmp_path / "worker.json"
    supervisor = PersistentSupervisor("android-1", path)
    supervisor.start()
    supervisor.heartbeat(now=100.0)
    supervisor.record_recovered_jobs(2)

    restored = PersistentSupervisor("android-1", path)
    assert restored.state.status == "ready"
    assert restored.state.last_heartbeat == 100.0
    assert restored.state.recovered_jobs == 2


def test_watchdog_requests_reconnect_after_timeout(tmp_path):
    supervisor = PersistentSupervisor("android-1", tmp_path / "worker.json")
    supervisor.heartbeat(now=100.0)
    assert supervisor.watchdog(now=150.0, timeout=40) == "reconnect"
    assert supervisor.state.status == "offline"


def test_watchdog_accepts_fresh_heartbeat(tmp_path):
    supervisor = PersistentSupervisor("android-1", tmp_path / "worker.json")
    supervisor.heartbeat(now=100.0)
    assert supervisor.watchdog(now=120.0, timeout=40) == "healthy"


def test_restart_failure_moves_worker_offline(tmp_path):
    supervisor = PersistentSupervisor("android-1", tmp_path / "worker.json")
    supervisor.start()

    def fail():
        raise RuntimeError("worker crashed")

    with pytest.raises(RuntimeError):
        supervisor.request_restart(fail)
    assert supervisor.state.status == "offline"
    assert supervisor.state.restart_count == 1


def test_stop_is_terminal(tmp_path):
    supervisor = PersistentSupervisor("android-1", tmp_path / "worker.json")
    supervisor.start()
    supervisor.stop()
    assert supervisor.state.status == "stopped"
    with pytest.raises(RuntimeError):
        supervisor.request_restart(lambda: None)


def test_identity_mismatch_fails_closed(tmp_path):
    path = tmp_path / "worker.json"
    supervisor = PersistentSupervisor("android-1", path)
    supervisor.start()
    data = json.loads(path.read_text())
    data["worker_id"] = "other-worker"
    path.write_text(json.dumps(data))

    with pytest.raises(ValueError, match="identity"):
        PersistentSupervisor("android-1", path)
