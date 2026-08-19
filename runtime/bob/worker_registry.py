"""Worker identity, capability and heartbeat lifecycle for PROJECT-BOB."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .worker_protocol import WorkerRegistration


@dataclass(frozen=True)
class WorkerRecord:
    worker_id: str
    platform: str
    capabilities: frozenset[str]
    status: str = "available"
    last_seen: float = 0.0
    resources: dict[str, float] = field(default_factory=dict)

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities


class WorkerRegistry:
    def __init__(self, heartbeat_timeout_seconds: float = 60.0) -> None:
        if heartbeat_timeout_seconds <= 0:
            raise ValueError("heartbeat timeout must be positive")
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self._workers: dict[str, WorkerRecord] = {}

    def register_worker(self, registration: WorkerRegistration, now: float = 0.0) -> WorkerRecord:
        record = WorkerRecord(
            registration.worker_id,
            registration.platform,
            registration.capabilities,
            "available",
            now,
            dict(registration.resources),
        )
        self._workers[record.worker_id] = record
        return record

    def heartbeat(
        self,
        worker_id: str,
        auth_identity: str,
        now: float,
        resources: dict[str, float] | None = None,
    ) -> WorkerRecord:
        if worker_id != auth_identity:
            raise PermissionError("worker identity mismatch")
        current = self._workers.get(worker_id)
        if current is None:
            raise KeyError(f"worker not registered: {worker_id}")
        updated = WorkerRecord(
            current.worker_id,
            current.platform,
            current.capabilities,
            "available",
            now,
            dict(current.resources if resources is None else resources),
        )
        self._workers[worker_id] = updated
        return updated

    def get(self, worker_id: str) -> WorkerRecord | None:
        return self._workers.get(worker_id)

    def available(self, capability: str) -> list[WorkerRecord]:
        return sorted(
            (w for w in self._workers.values() if w.status == "available" and w.supports(capability)),
            key=lambda w: w.worker_id,
        )

    def all(self) -> Iterable[WorkerRecord]:
        return tuple(self._workers.values())

    def expire_workers(self, now: float) -> list[str]:
        expired: list[str] = []
        for worker_id, worker in tuple(self._workers.items()):
            if worker.status == "available" and now - worker.last_seen > self.heartbeat_timeout_seconds:
                self._workers[worker_id] = WorkerRecord(
                    worker.worker_id,
                    worker.platform,
                    worker.capabilities,
                    "offline",
                    worker.last_seen,
                    dict(worker.resources),
                )
                expired.append(worker_id)
        return expired
