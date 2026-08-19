"""Typed contracts for the PROJECT-BOB distributed worker protocol."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Platform = Literal["android", "pc", "tablet"]
JobResultStatus = Literal["succeeded", "failed", "cancelled"]


@dataclass(frozen=True)
class WorkerRegistration:
    worker_id: str
    platform: Platform
    capabilities: frozenset[str] = field(default_factory=frozenset)
    resources: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.worker_id, str) or not self.worker_id.strip():
            raise ValueError("worker_id must not be empty")
        if self.platform not in {"android", "pc", "tablet"}:
            raise ValueError("unsupported worker platform")
        if any(not isinstance(cap, str) or not cap.strip() for cap in self.capabilities):
            raise ValueError("capabilities must contain non-empty strings")


@dataclass(frozen=True)
class JobResult:
    job_id: str
    lease_id: str
    status: JobResultStatus
    output: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.job_id.strip() or not self.lease_id.strip():
            raise ValueError("job_id and lease_id must not be empty")
        if self.status not in {"succeeded", "failed", "cancelled"}:
            raise ValueError("unsupported job result status")
