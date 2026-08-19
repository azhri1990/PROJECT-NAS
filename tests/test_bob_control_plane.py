import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "07-AUTOMATION"))

from bob.device_registry import Device, DeviceRegistry
from bob.job_queue import JobQueue, JobState
from bob.task_router import TaskRouter


def test_routes_to_lowest_cost_online_worker() -> None:
    devices = DeviceRegistry()
    devices.register(Device("phone", "android", frozenset({"lint"}), True, 0.0))
    devices.register(Device("pc", "windows", frozenset({"lint"}), True, 0.5))
    queue = JobQueue()
    job = queue.create("lint repository", "lint")

    route = TaskRouter(devices, queue).route(job)

    assert route.worker_id == "phone"
    assert route.state is JobState.DISPATCHED
    assert queue.get(job.job_id).worker_id == "phone"


def test_blocks_when_no_worker_is_available() -> None:
    devices = DeviceRegistry()
    devices.register(Device("phone", "android", frozenset({"lint"}), False))
    queue = JobQueue()
    job = queue.create("run tests", "pytest")

    route = TaskRouter(devices, queue).route(job)

    assert route.worker_id is None
    assert route.state is JobState.BLOCKED
    assert "pytest" in (route.reason or "")
