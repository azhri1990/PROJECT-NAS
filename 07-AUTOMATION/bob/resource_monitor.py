"""Resource-aware scheduling inputs for PROJECT-BOB.

The monitor is deliberately provider-neutral so Android, tablet, and PC workers
can report their own resource state without BOB gaining host-level authority.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceSnapshot:
    """Point-in-time worker resource information."""

    online: bool = True
    cpu_load: float = 0.0
    memory_available_mb: int = 0
    storage_available_mb: int = 0
    inference_available: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.cpu_load <= 1.0:
            raise ValueError("cpu_load must be between 0 and 1")
        for name in ("memory_available_mb", "storage_available_mb"):
            if not isinstance(getattr(self, name), int) or getattr(self, name) < 0:
                raise ValueError(f"{name} must be a non-negative integer")


class ResourceMonitor:
    """In-memory resource registry; workers remain responsible for reporting data."""

    def __init__(self) -> None:
        self._snapshots: dict[str, ResourceSnapshot] = {}

    def update(self, device_id: str, snapshot: ResourceSnapshot) -> None:
        if not isinstance(device_id, str) or not device_id.strip():
            raise ValueError("device_id must not be empty")
        self._snapshots[device_id.strip()] = snapshot

    def get(self, device_id: str) -> ResourceSnapshot | None:
        return self._snapshots.get(device_id)

    def eligible(self, device_id: str, *, max_cpu_load: float = 0.90, min_memory_mb: int = 0) -> bool:
        snapshot = self.get(device_id)
        return bool(
            snapshot
            and snapshot.online
            and snapshot.cpu_load <= max_cpu_load
            and snapshot.memory_available_mb >= min_memory_mb
        )
