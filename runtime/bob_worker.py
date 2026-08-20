"""Bounded worker for PROJECT-BOB.

The worker only processes jobs already admitted by BobControlLoop. It never
creates authority, bypasses policy, or retries indefinitely. When configured
with a local SQLite path it can recover and continue queued work after restart.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from runtime.bob_control_loop import BobControlLoop
from runtime.bob_persistent_queue import PersistentJobQueue
from runtime.policy import Capability, RiskLevel


@dataclass(frozen=True)
class WorkerConfig:
    max_iterations: int = 100
    idle_sleep_seconds: float = 0.25

    def __post_init__(self) -> None:
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be positive")
        if self.idle_sleep_seconds < 0:
            raise ValueError("idle_sleep_seconds cannot be negative")


class BobWorker:
    """Run a bounded number of admitted BOB jobs and then stop."""

    def __init__(
        self,
        control_loop: BobControlLoop | None = None,
        *,
        config: WorkerConfig | None = None,
        sleep: Callable[[float], None] = time.sleep,
        db_path: str | Path | None = None,
    ) -> None:
        if control_loop is not None and db_path is not None:
            raise ValueError("provide control_loop or db_path, not both")
        if db_path is not None:
            queue = PersistentJobQueue(db_path)
            queue.recover_running()
            control_loop = BobControlLoop(queue=queue)
        self.control_loop = control_loop or BobControlLoop()
        self.config = config or WorkerConfig()
        self._sleep = sleep
        self._stop_requested = False

    def stop(self) -> None:
        self._stop_requested = True

    def close(self) -> None:
        queue = self.control_loop.queue
        if isinstance(queue, PersistentJobQueue):
            queue.close()

    def submit_safe_read(self, task: str) -> str:
        job = self.control_loop.submit(
            task,
            Capability.READ_REPOSITORY.value,
            risk=RiskLevel.LOW.value,
        )
        return job.job_id

    def run(self, *, job_ids: list[str] | None = None) -> list[str]:
        """Process queued jobs, bounded by max_iterations.

        With a persistent queue, omitting ``job_ids`` drains available queued
        work up to the configured bound. The worker still stops after the
        bound or an explicit stop request.
        """
        completed: list[str] = []
        if job_ids is None:
            queue = self.control_loop.queue
            if not isinstance(queue, PersistentJobQueue):
                raise ValueError("job_ids are required for an in-memory queue")
            candidates = [job.job_id for job in queue.queued(self.config.max_iterations)]
        else:
            candidates = list(job_ids)

        for _ in range(self.config.max_iterations):
            if self._stop_requested or not candidates:
                break
            job_id = candidates.pop(0)
            result = self.control_loop.run_once(job_id)
            completed.append(result.job_id)
            if candidates and self.config.idle_sleep_seconds:
                self._sleep(self.config.idle_sleep_seconds)
        return completed
