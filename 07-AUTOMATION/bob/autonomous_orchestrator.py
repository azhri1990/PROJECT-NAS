"""Bounded autonomous build orchestration for PROJECT-BOB.

BOB plans, schedules, retries, and recovers jobs. It never executes arbitrary
commands itself; workers and the NAS policy/tool gateway remain authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .job_queue import Job, JobQueue, JobState
from .resource_monitor import ResourceMonitor


class RecoveryAction(StrEnum):
    RETRY = "retry"
    DEFER = "defer"
    BLOCK = "block"
    NONE = "none"


@dataclass(frozen=True)
class ResourceRequirements:
    min_memory_mb: int = 0
    max_cpu_load: float = 0.90
    requires_inference: bool = False


@dataclass(frozen=True)
class OrchestrationDecision:
    job_id: str
    action: RecoveryAction
    worker_id: str | None = None
    reason: str | None = None
    attempt: int = 0


class AutonomousOrchestrator:
    """Deterministic scheduler with bounded retries and resource-aware deferral."""

    def __init__(self, queue: JobQueue, resources: ResourceMonitor, *, max_retries: int = 2) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        self.queue = queue
        self.resources = resources
        self.max_retries = max_retries
        self._attempts: dict[str, int] = {}

    def attempt(self, job: Job, *, worker_id: str | None, requirements: ResourceRequirements | None = None) -> OrchestrationDecision:
        requirements = requirements or ResourceRequirements()
        attempt = self._attempts.get(job.job_id, 0)

        if worker_id is None:
            self.queue.update(job.job_id, state=JobState.BLOCKED, reason="no worker available")
            return OrchestrationDecision(job.job_id, RecoveryAction.BLOCK, reason="no worker available", attempt=attempt)

        snapshot = self.resources.get(worker_id)
        if snapshot is None or not snapshot.online:
            return self._recover(job, "worker offline", attempt)
        if snapshot.cpu_load > requirements.max_cpu_load:
            return OrchestrationDecision(job.job_id, RecoveryAction.DEFER, worker_id, "worker CPU load too high", attempt)
        if snapshot.memory_available_mb < requirements.min_memory_mb:
            return OrchestrationDecision(job.job_id, RecoveryAction.DEFER, worker_id, "insufficient memory", attempt)
        if requirements.requires_inference and not snapshot.inference_available:
            return OrchestrationDecision(job.job_id, RecoveryAction.DEFER, worker_id, "local inference unavailable", attempt)

        self.queue.update(job.job_id, state=JobState.RUNNING, worker_id=worker_id, reason=None)
        return OrchestrationDecision(job.job_id, RecoveryAction.NONE, worker_id, attempt=attempt)

    def failure(self, job: Job, reason: str) -> OrchestrationDecision:
        attempt = self._attempts.get(job.job_id, 0) + 1
        self._attempts[job.job_id] = attempt
        return self._recover(job, reason, attempt)

    def success(self, job: Job) -> OrchestrationDecision:
        self.queue.update(job.job_id, state=JobState.SUCCEEDED, reason=None)
        return OrchestrationDecision(job.job_id, RecoveryAction.NONE, worker_id=job.worker_id, attempt=self._attempts.get(job.job_id, 0))

    def _recover(self, job: Job, reason: str, attempt: int) -> OrchestrationDecision:
        if attempt <= self.max_retries:
            self.queue.update(job.job_id, state=JobState.QUEUED, reason=reason)
            return OrchestrationDecision(job.job_id, RecoveryAction.RETRY, reason=reason, attempt=attempt)
        self.queue.update(job.job_id, state=JobState.FAILED, reason=reason)
        return OrchestrationDecision(job.job_id, RecoveryAction.BLOCK, reason=f"retry budget exhausted: {reason}", attempt=attempt)
