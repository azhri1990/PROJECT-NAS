"""BOB-6 worker discovery and capability ranking primitives.

Discovery is advisory: worker capability never grants execution authority.
NAS PolicyEngine/ToolGateway remains authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True)
class WorkerSnapshot:
    worker_id: str
    platform: str
    capabilities: frozenset[str] = field(default_factory=frozenset)
    online: bool = False
    cpu_available: float = 0.0
    memory_available_mb: int = 0
    last_seen: datetime | None = None

    def is_fresh(self, now: datetime, timeout_seconds: int = 90) -> bool:
        if not self.online or self.last_seen is None:
            return False
        return (now - self.last_seen).total_seconds() <= timeout_seconds


def rank_workers(
    workers: Iterable[WorkerSnapshot],
    required_capabilities: Iterable[str] = (),
    *,
    now: datetime | None = None,
    timeout_seconds: int = 90,
) -> list[WorkerSnapshot]:
    """Return eligible workers ordered by capability fit and free resources."""
    now = now or datetime.now(timezone.utc)
    required = frozenset(required_capabilities)
    eligible = [
        worker
        for worker in workers
        if worker.is_fresh(now, timeout_seconds)
        and required.issubset(worker.capabilities)
    ]
    return sorted(
        eligible,
        key=lambda w: (-len(w.capabilities & required), -w.cpu_available, -w.memory_available_mb, w.worker_id),
    )


def choose_worker(
    workers: Iterable[WorkerSnapshot],
    required_capabilities: Iterable[str] = (),
    *,
    now: datetime | None = None,
    timeout_seconds: int = 90,
) -> WorkerSnapshot | None:
    ranked = rank_workers(
        workers,
        required_capabilities,
        now=now,
        timeout_seconds=timeout_seconds,
    )
    return ranked[0] if ranked else None
