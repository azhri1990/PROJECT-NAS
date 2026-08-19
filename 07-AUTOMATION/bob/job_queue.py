"""Deterministic, in-memory job queue primitives for PROJECT-BOB."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from uuid import uuid4


class JobState(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Job:
    job_id: str
    task: str
    capability: str
    state: JobState = JobState.CREATED
    worker_id: str | None = None
    reason: str | None = None


class JobQueue:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create(self, task: str, capability: str) -> Job:
        if not isinstance(task, str) or not isinstance(capability, str):
            raise ValueError("task and capability must be strings")
        if not task.strip() or not capability.strip():
            raise ValueError("task and capability must not be empty")
        job = Job(uuid4().hex, task.strip(), capability.strip())
        self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def update(self, job_id: str, **changes: object) -> Job:
        current = self._jobs[job_id]
        job = replace(current, **changes)
        self._jobs[job_id] = job
        return job

    def cancel(self, job_id: str) -> Job:
        current = self._jobs[job_id]
        if current.state in {JobState.RUNNING, JobState.SUCCEEDED, JobState.FAILED, JobState.BLOCKED, JobState.CANCELLED}:
            raise ValueError(f"job cannot be cancelled from state: {current.state.value}")
        return self.update(job_id, state=JobState.CANCELLED, reason="cancelled by operator")

    def all(self) -> tuple[Job, ...]:
        return tuple(self._jobs.values())