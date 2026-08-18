"""Fail-closed, capability-based policy for JARVIS orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Capability(str, Enum):
    READ_REPOSITORY = "read_repository"
    READ_RUNTIME = "read_runtime"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    NETWORK_LOCAL = "network_local"
    EXECUTE_SAFE = "execute_safe"
    SYSTEM_MUTATION = "system_mutation"
    EXTERNAL_NETWORK = "external_network"


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    reason: str
    capability: Capability | None = None
    risk: str = "low"


_READ_ONLY = {
    Capability.READ_REPOSITORY,
    Capability.READ_RUNTIME,
    Capability.MEMORY_READ,
}


class PolicyEngine:
    """Deterministic policy engine. Invalid input fails closed."""

    def evaluate(
        self,
        *,
        tool_name: str,
        capability: Capability | str,
        risk: str,
        payload: dict[str, Any],
    ) -> PolicyDecision:
        if not isinstance(tool_name, str) or not tool_name.strip():
            return PolicyDecision(Decision.DENY, "invalid tool name")
        if not isinstance(payload, dict):
            return PolicyDecision(Decision.DENY, "invalid tool payload")
        try:
            cap = capability if isinstance(capability, Capability) else Capability(capability)
        except (TypeError, ValueError) as exc:
            raise ValueError("unknown capability") from exc
        if risk not in {"low", "medium", "high", "critical"}:
            return PolicyDecision(Decision.DENY, "invalid risk level", cap, "invalid")
        if cap == Capability.EXTERNAL_NETWORK:
            return PolicyDecision(Decision.DENY, "capability external_network is disabled by default", cap, risk)
        if cap == Capability.SYSTEM_MUTATION:
            return PolicyDecision(Decision.DENY, "capability system_mutation requires explicit approval", cap, risk)
        if cap == Capability.EXECUTE_SAFE and risk != "low":
            return PolicyDecision(Decision.REQUIRE_CONFIRMATION, "capability execute_safe requires confirmation at this risk level", cap, risk)
        if cap in {Capability.MEMORY_WRITE, Capability.NETWORK_LOCAL}:
            return PolicyDecision(Decision.REQUIRE_CONFIRMATION, f"capability {cap.value} requires explicit confirmation", cap, risk)
        if cap in _READ_ONLY and risk in {"low", "medium"}:
            return PolicyDecision(Decision.ALLOW, "allowed by local least-privilege policy", cap, risk)
        return PolicyDecision(Decision.DENY, f"capability {cap.value} is not allowed by the current policy", cap, risk)
