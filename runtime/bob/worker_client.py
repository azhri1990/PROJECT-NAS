"""Platform-neutral HTTP client for BOB workers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .worker_protocol import JobResult, WorkerRegistration


@dataclass
class WorkerClient:
    request: Callable[[str, dict[str, Any]], dict[str, Any]]
    registration: WorkerRegistration
    now: float = 0.0

    def register(self) -> dict[str, Any]:
        return self.request("/workers/register", {
            "worker_id": self.registration.worker_id,
            "platform": self.registration.platform,
            "capabilities": sorted(self.registration.capabilities),
            "resources": self.registration.resources,
            "now": self.now,
        })

    def heartbeat(self, resources: dict[str, float] | None = None) -> dict[str, Any]:
        return self.request("/workers/heartbeat", {
            "worker_id": self.registration.worker_id,
            "resources": resources or self.registration.resources,
            "now": self.now,
        })

    def claim(self, job_id: str, capability: str) -> dict[str, Any]:
        return self.request("/jobs/claim", {
            "job_id": job_id,
            "worker_id": self.registration.worker_id,
            "capability": capability,
            "now": self.now,
        })

    def report(self, result: JobResult) -> dict[str, Any]:
        return self.request("/jobs/result", {
            "job_id": result.job_id,
            "lease_id": result.lease_id,
            "worker_id": self.registration.worker_id,
            "status": result.status,
            "output": result.output,
            "now": self.now,
        })
