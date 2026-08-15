from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ActionRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Capability(str, Enum):
    PROVIDER_HEALTH = "provider.health"
    PROVIDER_CHAT = "provider.chat"
    DEVICE_CONTROL = "device.control"
    TERMINAL = "device.terminal"
    FILESYSTEM_WRITE = "device.filesystem.write"
    DESTRUCTIVE = "device.destructive"


@dataclass(frozen=True)
class PolicyRequest:
    action: str
    capability: Capability
    risk: ActionRisk
    human_approved: bool = False

    def __post_init__(self) -> None:
        if not self.action.strip():
            raise ValueError("action must not be blank")
        if not isinstance(self.capability, Capability):
            raise ValueError("capability must be a Capability")
        if not isinstance(self.risk, ActionRisk):
            raise ValueError("risk must be an ActionRisk")


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str

    @classmethod
    def allow(cls, reason: str) -> "PolicyDecision":
        return cls(True, reason)

    @classmethod
    def deny(cls, reason: str) -> "PolicyDecision":
        return cls(False, reason)


class PolicyEngine:
    """Deterministic policy boundary; model output never changes these rules."""

    _SAFE_DEFAULTS = {Capability.PROVIDER_HEALTH, Capability.PROVIDER_CHAT}
    _APPROVAL_REQUIRED = {
        Capability.DEVICE_CONTROL,
        Capability.TERMINAL,
        Capability.FILESYSTEM_WRITE,
        Capability.DESTRUCTIVE,
    }

    def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        if request.capability in self._SAFE_DEFAULTS and request.risk is ActionRisk.LOW:
            return PolicyDecision.allow("local-first provider capability")

        if request.capability in self._APPROVAL_REQUIRED:
            if request.human_approved:
                return PolicyDecision.allow("explicit human approval")
            return PolicyDecision.deny("human approval required")

        return PolicyDecision.deny("capability not permitted by policy")
