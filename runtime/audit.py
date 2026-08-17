from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    """Immutable record of a tool-gateway authorization decision."""

    tool: str
    allowed: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {"tool": self.tool, "allowed": self.allowed, "reason": self.reason}


class AuditLog:
    """Bounded, list-compatible audit history for local runtime decisions."""

    def __init__(self, limit: int = 100):
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("audit_limit must be positive")
        self._limit = limit
        self._events: list[AuditEvent] = []

    def record(self, tool: str, allowed: bool, reason: str) -> None:
        self._events.append(AuditEvent(tool, bool(allowed), reason))
        if len(self._events) > self._limit:
            del self._events[: len(self._events) - self._limit]

    def snapshot(self) -> list[dict[str, object]]:
        return [event.as_dict() for event in self._events]

    def __len__(self) -> int:
        return len(self._events)

    def __getitem__(self, index: int | slice) -> dict[str, object] | list[dict[str, object]]:
        snapshot = self.snapshot()
        return snapshot[index]

    def __iter__(self):
        return iter(self.snapshot())
