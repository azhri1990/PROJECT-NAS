from datetime import datetime, timedelta, timezone

from runtime.bob.discovery import WorkerSnapshot, choose_worker, rank_workers


def test_choose_worker_prefers_capability_and_resources():
    now = datetime.now(timezone.utc)
    workers = [
        WorkerSnapshot("android", "android", frozenset({"python"}), True, 0.4, 1024, now),
        WorkerSnapshot("pc", "windows", frozenset({"python", "build"}), True, 0.8, 8192, now),
    ]
    assert choose_worker(workers, {"build"}, now=now).worker_id == "pc"


def test_stale_worker_is_not_eligible():
    now = datetime.now(timezone.utc)
    stale = WorkerSnapshot(
        "pc", "windows", frozenset({"build"}), True, 1.0, 8192,
        now - timedelta(seconds=91),
    )
    assert rank_workers([stale], {"build"}, now=now) == []


def test_missing_capability_blocks_worker():
    now = datetime.now(timezone.utc)
    worker = WorkerSnapshot("android", "android", frozenset({"python"}), True, 1.0, 4096, now)
    assert choose_worker([worker], {"build"}, now=now) is None
