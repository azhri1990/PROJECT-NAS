from pathlib import Path

from runtime.bob_worker import BobWorker, WorkerConfig
from runtime.policy import Capability


def test_persistent_worker_processes_queued_job(tmp_path: Path):
    db = tmp_path / "bob.sqlite3"
    worker = BobWorker(config=WorkerConfig(max_iterations=2, idle_sleep_seconds=0), db_path=db)
    job_id = worker.submit_safe_read("inspect repository")
    assert worker.run() == [job_id]
    assert worker.control_loop.queue.get(job_id).state.value == "succeeded"
    worker.close()


def test_persistent_worker_recovers_running_job(tmp_path: Path):
    db = tmp_path / "bob.sqlite3"
    first = BobWorker(config=WorkerConfig(max_iterations=1, idle_sleep_seconds=0), db_path=db)
    job_id = first.submit_safe_read("inspect repository")
    first.control_loop.queue.update(job_id, state="running", worker_id="crashed-worker")
    first.close()

    second = BobWorker(config=WorkerConfig(max_iterations=1, idle_sleep_seconds=0), db_path=db)
    recovered = second.control_loop.queue.get(job_id)
    assert recovered.state.value == "queued"
    assert recovered.reason == "recovered after worker restart"
    assert second.run() == [job_id]
    assert second.control_loop.queue.get(job_id).state.value == "succeeded"
    second.close()


def test_persistent_worker_preserves_governed_submission(tmp_path: Path):
    db = tmp_path / "bob.sqlite3"
    worker = BobWorker(config=WorkerConfig(max_iterations=1, idle_sleep_seconds=0), db_path=db)
    job = worker.control_loop.submit("inspect repository", Capability.READ_REPOSITORY.value)
    assert job.state.value == "queued"
    assert worker.run() == [job.job_id]
    assert worker.control_loop.queue.get(job.job_id).state.value == "succeeded"
    worker.close()


def test_worker_rejects_mixed_persistent_configuration(tmp_path: Path):
    from runtime.bob_control_loop import BobControlLoop

    try:
        BobWorker(BobControlLoop(), db_path=tmp_path / "bob.sqlite3")
    except ValueError:
        pass
    else:
        raise AssertionError("expected mixed worker configuration to fail")
