from pathlib import Path

from runtime.bob_autopilot_daemon import SingleInstance


def test_single_instance_allows_one_owner(tmp_path: Path):
    lock = SingleInstance(tmp_path / "bob.lock")
    assert lock.acquire()
    second = SingleInstance(tmp_path / "bob.lock")
    assert not second.acquire()
    lock.release()
    assert second.acquire()
    second.release()


def test_stale_pid_lock_is_reclaimed(tmp_path: Path):
    lock = tmp_path / "bob.lock"
    lock.write_text("999999999", encoding="utf-8")

    instance = SingleInstance(lock)
    assert instance.acquire() is True
    assert lock.read_text(encoding="utf-8").strip() != "999999999"
    instance.release()
    assert not lock.exists()
