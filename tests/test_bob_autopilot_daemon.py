from pathlib import Path

from runtime.bob_autopilot_daemon import SingleInstance


def test_single_instance_allows_one_owner(tmp_path: Path):
    lock = SingleInstance(tmp_path / 'bob.lock')
    assert lock.acquire()
    second = SingleInstance(tmp_path / 'bob.lock')
    assert not second.acquire()
    lock.release()
    assert second.acquire()
    second.release()
