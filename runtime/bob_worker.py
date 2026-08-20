"""Bounded worker for PROJECT-BOB.

The worker only processes jobs already admitted by BobControlLoop. It never
creates authority, bypasses policy, or retries indefinitely.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from runtime.bob_control_loop import BobControlLoop
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
    ) -> None:
        self.control_loop = control_loop or BobControlLoop()
        self.config = config or WorkerConfig()
        self._sleep = sleep
        self._stop_requested = False

    def stop(self) -> None:
        self._stop_requested = True

    def submit_safe_read(self, task: str) -> str:
        job = self.control_loop.submit(
            task,
            Capability.READ_REPOSITORY.value,
            risk=RiskLevel.LOW.value,
        )
        return job.job_id

    def run(self, *, job_ids: list[str] | None = None) -> list[str]:
        """Process supplied queued jobs, bounded by max_iterations."""
        completed: list[str] = []
        candidates = list(job_ids or [])
        for _ in range(self.config.max_iterations):
            if self._stop_requested or not candidates:
                break
            job_id = candidates.pop(0)
            result = self.control_loop.run_once(job_id)
            completed.append(result.job_id)
            if candidates and self.config.idle_sleep_seconds:
                self._sleep(self.config.idle_sleep_seconds)
        return completed
