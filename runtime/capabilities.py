"""Discoverable JARVIS capabilities without implicit execution authority."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    category: str
    description: str
    provider: str
    cost: str = "free"
    authorizes_execution: bool = False


class CapabilityRegistry:
    """Allowlisted capability metadata; registration never grants authority."""

    def __init__(self) -> None:
        self._capabilities: dict[str, CapabilitySpec] = {}

    def register(self, spec: CapabilitySpec) -> None:
        if not spec.name.strip():
            raise ValueError("capability name must not be empty")
        if spec.name in self._capabilities:
            raise ValueError(f"capability already registered: {spec.name}")
        if not spec.description.strip():
            raise ValueError("capability description must not be empty")
        if not spec.provider.strip():
            raise ValueError("capability provider must not be empty")
        if spec.authorizes_execution:
            raise ValueError("capability metadata cannot grant execution authority")
        self._capabilities[spec.name] = spec

    def get(self, name: str) -> CapabilitySpec:
        try:
            return self._capabilities[name]
        except KeyError as exc:
            raise KeyError(f"unknown capability: {name}") from exc

    def list(self) -> tuple[CapabilitySpec, ...]:
        return tuple(self._capabilities[name] for name in sorted(self._capabilities))
