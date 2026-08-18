"""Resource-aware, local-only model selection for PROJECT-NAS."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable


class TaskComplexity(str, Enum):
    SIMPLE = "simple"
    NORMAL = "normal"
    COMPLEX = "complex"


@dataclass(frozen=True)
class ResourceSnapshot:
    ram_available_mb: int
    cpu_load_ratio: float
    cpu_count: int

    def __post_init__(self) -> None:
        if self.ram_available_mb < 0:
            raise ValueError("ram_available_mb must be non-negative")
        if not 0.0 <= self.cpu_load_ratio:
            raise ValueError("cpu_load_ratio must be non-negative")
        if self.cpu_count < 1:
            raise ValueError("cpu_count must be positive")


@dataclass(frozen=True)
class ResourceAwareRoute:
    configured: str
    selected: str | None
    available: tuple[str, ...]
    fallback: bool
    reason: str


class ResourceAwareModelRouter:
    """Select the strongest safe local model that fits current resource pressure."""

    def __init__(
        self,
        configured_model: str,
        *,
        preferred_models: tuple[str, ...] = ("llama3.2:3b", "llama3.2:1b", "llama3.1:8b"),
        resource_reader: Callable[[], ResourceSnapshot] | None = None,
    ) -> None:
        if not isinstance(configured_model, str) or not configured_model.strip():
            raise ValueError("configured_model must be a non-empty string")
        self.configured_model = configured_model.strip()
        self.preferred_models = tuple(dict.fromkeys((self.configured_model, *preferred_models)))
        self._resource_reader = resource_reader or read_local_resources

    @staticmethod
    def _safe_local_model_names(available: Iterable[str]) -> tuple[str, ...]:
        # Model identifiers are Ollama names, never URLs or arbitrary endpoints.
        names = {
            name.strip()
            for name in available
            if isinstance(name, str)
            and name.strip()
            and "://" not in name
            and "/" not in name
            and "\\" not in name
            and len(name.strip()) <= 128
        }
        return tuple(sorted(names))

    @staticmethod
    def _resource_pressure(resources: ResourceSnapshot) -> bool:
        return resources.ram_available_mb < 1024 or resources.cpu_load_ratio >= 0.85

    def route(
        self,
        *,
        available: Iterable[str],
        complexity: TaskComplexity,
        resources: ResourceSnapshot | None = None,
    ) -> ResourceAwareRoute:
        if not isinstance(complexity, TaskComplexity):
            try:
                complexity = TaskComplexity(complexity)
            except (TypeError, ValueError) as exc:
                raise ValueError("complexity must be simple, normal, or complex") from exc

        names = self._safe_local_model_names(available)
        resources = resources or self._resource_reader()
        pressured = self._resource_pressure(resources)

        # On constrained hardware, prefer the smallest known model. Never invent
        # or download a model, and never route to an external endpoint.
        if pressured:
            candidates = tuple(name for name in ("llama3.2:1b", "llama3.2:3b") if name in names)
            selected = candidates[0] if candidates else next((n for n in self.preferred_models if n in names), None)
        elif complexity is TaskComplexity.COMPLEX:
            selected = next((n for n in self.preferred_models if n in names and n != "llama3.2:1b"), None)
            selected = selected or next((n for n in self.preferred_models if n in names), None)
        else:
            selected = next((n for n in self.preferred_models if n in names), None)

        if selected is None:
            return ResourceAwareRoute(
                configured=self.configured_model,
                selected=None,
                available=names,
                fallback=False,
                reason="no local model available",
            )

        fallback = selected != self.configured_model
        reason = "resource pressure" if pressured and fallback else "configured model" if not fallback else "preferred local fallback"
        return ResourceAwareRoute(
            configured=self.configured_model,
            selected=selected,
            available=names,
            fallback=fallback,
            reason=reason,
        )

    def discover_route(self, available: Iterable[str], complexity: TaskComplexity) -> ResourceAwareRoute:
        return self.route(available=available, complexity=complexity)


def read_local_resources() -> ResourceSnapshot:
    """Read lightweight OS metrics without requiring psutil or cloud services."""
    ram_available_mb = _read_mem_available_mb()
    cpu_count = max(1, os.cpu_count() or 1)
    cpu_load_ratio = _read_cpu_load_ratio(cpu_count)
    return ResourceSnapshot(
        ram_available_mb=ram_available_mb,
        cpu_load_ratio=cpu_load_ratio,
        cpu_count=cpu_count,
    )


def _read_mem_available_mb() -> int:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return 0
    try:
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                kb = int(line.split()[1])
                return max(0, kb // 1024)
    except (OSError, ValueError, IndexError):
        return 0
    return 0


def _read_cpu_load_ratio(cpu_count: int) -> float:
    try:
        load = os.getloadavg()[0]
    except (AttributeError, OSError):
        return 0.0
    return max(0.0, float(load) / max(1, cpu_count))
