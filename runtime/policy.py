from dataclasses import dataclass
from enum import Enum
from typing import Any


class Capability(str, Enum):
    READ_REPOSITORY = "read_repository"
    READ_RUNTIME = "read_runtime"
    WRITE_REPOSITORY = "write_repository"
    EXECUTE_PROCESS = "execute_process"
    NETWORK_ACCESS = "network_access"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ToolRequest:
    tool_name: str
    capability: Capability
    risk: RiskLevel
    input: dict[str, Any]


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


class PolicyEngine:
    """Deterministic local-first policy gate for tool requests."""

    def evaluate(self, request: ToolRequest) -> PolicyDecision:
        if request.capability in {
            Capability.EXECUTE_PROCESS,
            Capability.NETWORK_ACCESS,
        }:
            return PolicyDecision(
                False,
                f"capability {request.capability.value} denied by default",
            )

        if request.capability == Capability.WRITE_REPOSITORY:
            return PolicyDecision(
                False,
                "write_repository requires explicit approval",
            )

        if request.risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            return PolicyDecision(
                False,
                "high-risk action requires explicit approval",
            )

        return PolicyDecision(True, "allowed by local read-only policy")
