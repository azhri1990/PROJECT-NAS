"""Constrained autonomous decision loop for PROJECT-BOB.

Routine work may proceed automatically, while missing verification or elevated
risk fails closed and escalates to the operator.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AutopilotAction(StrEnum):
    PROCEED = "proceed"
    RETRY = "retry"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class AutopilotDecision:
    action: AutopilotAction
    reason: str
    attempt: int = 0


_HIGH_RISK = {"security", "destructive", "architectural", "cost", "network", "repository_mutation"}


def decide_next(
    *,
    risk: str,
    verified: bool,
    attempt: int,
    max_retries: int,
    failure_class: str | None = None,
) -> AutopilotDecision:
    """Return the next bounded action for routine autopilot execution."""
    if not isinstance(risk, str) or not risk.strip():
        raise ValueError("risk must not be empty")
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 0:
        raise ValueError("attempt must be a non-negative integer")
    if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
        raise ValueError("max_retries must be a non-negative integer")

    normalized_risk = risk.strip().lower()
    if normalized_risk in _HIGH_RISK:
        return AutopilotDecision(
            AutopilotAction.ESCALATE,
            f"{normalized_risk} risk requires operator approval",
            attempt,
        )

    if verified:
        return AutopilotDecision(
            AutopilotAction.PROCEED,
            "routine work is verified",
            attempt,
        )

    if attempt < max_retries:
        label = failure_class or "unclassified_failure"
        return AutopilotDecision(
            AutopilotAction.RETRY,
            f"retrying bounded failure class: {label}",
            attempt + 1,
        )

    return AutopilotDecision(
        AutopilotAction.ESCALATE,
        "verification is missing and retry budget is exhausted",
        attempt,
    )
