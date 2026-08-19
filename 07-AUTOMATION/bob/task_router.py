"""Policy-neutral worker routing for PROJECT-BOB."""

from __future__ import annotations

from dataclasses import dataclass

from .device_registry import DeviceRegistry
from .job_queue import Job, JobQueue, JobState


@dataclass(frozen=True)
class Route:
    worker_id: str | None
    state: JobState
    reason: str | None = None


class TaskRouter:
    """Select an available worker without granting execution authority."""

    def __init__(self, devices: DeviceRegistry, queue: JobQueue) -> None:
        self.devices = devices
        self.queue = queue

    def route(self, job: Job) -> Route:
        candidates = self.devices.available(job.capability)
        if not candidates:
            updated = self.queue.update(
                job.job_id,
                state=JobState.BLOCKED,
                reason=f"no online worker supports capability: {job.capability}",
            )
            return Route(None, updated.state, updated.reason)

        worker = candidates[0]
        updated = self.queue.update(
            job.job_id,
            state=JobState.DISPATCHED,
            worker_id=worker.device_id,
            reason=None,
        )
        return Route(worker.device_id, updated.state)
