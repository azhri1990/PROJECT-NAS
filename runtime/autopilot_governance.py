"""Deterministic governance primitives for PROJECT-BOB autonomous operation."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from runtime.policy import Capability, RiskLevel, ToolRequest


class DecisionClass(str, Enum):
    AUTO = "auto"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class GovernanceDecision:
    classification: DecisionClass
    reason: str


class AutopilotGovernance:
    """Fail-closed decision classifier layered above the existing policy engine."""

    def classify(self, request: ToolRequest) -> GovernanceDecision:
        if request.risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            return GovernanceDecision(
                DecisionClass.ESCALATE,
                "high or critical risk requires Nash approval",
            )

        if request.capability in {
            Capability.EXECUTE_PROCESS,
            Capability.NETWORK_ACCESS,
        }:
            return GovernanceDecision(
                DecisionClass.ESCALATE,
                "execution/network capability requires explicit approval",
            )

        if request.capability == Capability.WRITE_REPOSITORY:
            return GovernanceDecision(
                DecisionClass.ESCALATE,
                "repository mutation requires explicit approval",
            )

        if request.capability not in set(Capability):
            return GovernanceDecision(
                DecisionClass.ESCALATE,
                "unknown capability fails closed",
            )

        return GovernanceDecision(
            DecisionClass.AUTO,
            "bounded low-risk read operation may proceed autonomously",
        )
