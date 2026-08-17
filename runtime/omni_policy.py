"""Safe local-first policy planning for PROJECT-NAS Omni capabilities.

This module deliberately plans capabilities rather than executing them.  It is
safe to expose to a UI, voice layer, or future device bridge because every
requested action is classified before any privileged operation can occur.
"""

from dataclasses import dataclass
from enum import Enum


class OmniCapability(str, Enum):
    READ_MEMORY = "read_memory"
    READ_STATUS = "read_status"
    READ_REPOSITORY = "read_repository"
    WRITE_REPOSITORY = "write_repository"
    EXECUTE_PROCESS = "execute_process"
    NETWORK_ACCESS = "network_access"
    DEVICE_CONTROL = "device_control"


class Decision(str, Enum):
    ALLOW = "allow"
    APPROVAL_REQUIRED = "approval_required"
    DENY = "deny"


@dataclass(frozen=True)
class OmniRequest:
    capability: OmniCapability
    target: str = ""
    reason: str = ""


@dataclass(frozen=True)
class OmniDecision:
    decision: Decision
    reason: str


class OmniPolicy:
    """Deterministic policy boundary; no execution occurs here."""

    READ_ONLY = frozenset({
        OmniCapability.READ_MEMORY,
        OmniCapability.READ_STATUS,
        OmniCapability.READ_REPOSITORY,
    })

    def evaluate(self, request: OmniRequest) -> OmniDecision:
        if request.capability in self.READ_ONLY:
            return OmniDecision(Decision.ALLOW, "local read-only capability")

        if request.capability in {
            OmniCapability.WRITE_REPOSITORY,
            OmniCapability.DEVICE_CONTROL,
        }:
            return OmniDecision(Decision.APPROVAL_REQUIRED, "explicit approval required")

        if request.capability in {
            OmniCapability.EXECUTE_PROCESS,
            OmniCapability.NETWORK_ACCESS,
        }:
            return OmniDecision(Decision.DENY, "privileged capability denied by default")

        return OmniDecision(Decision.DENY, "unknown capability denied")
