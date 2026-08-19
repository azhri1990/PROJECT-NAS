"""Minimal in-memory audit sink for BOB worker lifecycle events."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkerEvent:
    event_type: str
    worker_id: str
    job_id: str | None = None
    details: dict[str, Any] | None = None


class WorkerAudit:
    def __init__(self) -> None:
        self._events: list[WorkerEvent] = []

    def record(self, event_type: str, worker_id: str, job_id: str | None = None, details: dict[str, Any] | None = None) -> None:
        if not event_type.strip() or not worker_id.strip():
            raise ValueError("event_type and worker_id must not be empty")
        safe = dict(details or {})
        safe.pop("authorization", None)
        safe.pop("token", None)
        self._events.append(WorkerEvent(event_type, worker_id, job_id, safe))

    def events(self) -> tuple[WorkerEvent, ...]:
        return tuple(self._events)
