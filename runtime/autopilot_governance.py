"""Deterministic governance primitives for PROJECT-BOB autonomous operation."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from runtime.policy import Capability, PolicyEngine, RiskLevel, ToolRequest


class DecisionClass(str, Enum):
    AUTO = "auto"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class GovernanceDecision:
    classification: DecisionClass
    reason: str


class AutopilotGovernance:
    """Fail-closed autonomy classifier layered above the NAS policy gate."""

    def __init__(self, policy_engine: PolicyEngine | None = None) -> None:
        self.policy_engine = policy_engine or PolicyEngine()

    def classify(self, request: ToolRequest) -> GovernanceDecision:
        policy = self.policy_engine.evaluate(request)
        if not policy.allowed:
            return GovernanceDecision(
                DecisionClass.ESCALATE,
                f"NAS policy denied autonomous execution: {policy.reason}",
            )

        if request.risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            return GovernanceDecision(
                DecisionClass.ESCALATE,
                "high or critical risk requires Nash approval",
            )

        if request.capability in {
            Capability.EXECUTE_PROCESS,
            Capability.NETWORK_ACCESS,
            Capability.WRITE_REPOSITORY,
        }:
            return GovernanceDecision(
                DecisionClass.ESCALATE,
                "capability requires explicit approval",
            )

        if request.capability not in set(Capability):
            return GovernanceDecision(
                DecisionClass.ESCALATE,
                "unknown capability fails closed",
            )

        return GovernanceDecision(
            DecisionClass.AUTO,
            "bounded low-risk read operation is permitted by NAS policy",
        )
