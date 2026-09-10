from runtime.bob_control_loop import BobControlLoop
from runtime.bob_worker import BobWorker, WorkerConfig
from runtime.policy import Capability


def test_worker_processes_admitted_job_and_stops():
    loop = BobControlLoop(executor=lambda job: True)
    worker = BobWorker(loop, config=WorkerConfig(max_iterations=1, idle_sleep_seconds=0))
    job = loop.submit("inspect repository", Capability.READ_REPOSITORY.value)
    assert job.state.value == "queued"
    assert worker.run(job_ids=[job.job_id]) == [job.job_id]
    assert loop.queue.get(job.job_id).state.value == "succeeded"


def test_worker_respects_stop_before_work():
    loop = BobControlLoop(executor=lambda job: True)
    worker = BobWorker(loop, config=WorkerConfig(max_iterations=10, idle_sleep_seconds=0))
    job = loop.submit("inspect repository", Capability.READ_REPOSITORY.value)
    worker.stop()
    assert worker.run(job_ids=[job.job_id]) == []
    assert loop.queue.get(job.job_id).state.value == "queued"


def test_worker_is_bounded():
    loop = BobControlLoop(executor=lambda job: True)
    worker = BobWorker(loop, config=WorkerConfig(max_iterations=2, idle_sleep_seconds=0))
    jobs = [
        loop.submit(f"inspect {i}", Capability.READ_REPOSITORY.value)
        for i in range(3)
    ]
    completed = worker.run(job_ids=[job.job_id for job in jobs])
    assert len(completed) == 2
    assert loop.queue.get(jobs[2].job_id).state.value == "queued"


def test_worker_rejects_invalid_bounds():
    try:
        WorkerConfig(max_iterations=0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected invalid worker bound to fail")
