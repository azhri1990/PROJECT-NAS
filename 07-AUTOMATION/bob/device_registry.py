"""Device capability and availability registry for PROJECT-BOB."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True)
class Device:
    device_id: str
    platform: str
    capabilities: frozenset[str] = field(default_factory=frozenset)
    online: bool = False
    cost: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities


class DeviceRegistry:
    def __init__(self) -> None:
        self._devices: dict[str, Device] = {}
        self._seen: dict[str, str] = {}

    def register(self, device: Device) -> None:
        if not device.device_id.strip():
            raise ValueError("device_id must not be empty")
        if not device.platform.strip():
            raise ValueError("platform must not be empty")
        self._devices[device.device_id] = device
        self._seen[device.device_id] = datetime.now(timezone.utc).isoformat()

    def get(self, device_id: str) -> Device | None:
        return self._devices.get(device_id)

    def available(self, capability: str) -> list[Device]:
        return sorted(
            (d for d in self._devices.values() if d.online and d.supports(capability)),
            key=lambda d: (d.cost, d.device_id),
        )

    def all(self) -> Iterable[Device]:
        return tuple(self._devices.values())

    def last_seen(self, device_id: str) -> str | None:
        return self._seen.get(device_id)
