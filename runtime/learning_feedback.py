"""Bounded outcome-to-learning feedback for PROJECT-NAS."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from runtime.adaptive_decision import OutcomeStatus


@dataclass(frozen=True)
class LearningFeedbackDecision:
    strengthen: bool
    weaken: bool
    revalidate: bool
    confidence_delta: float
    reason: str


class LearningFeedbackEngine:
    """Translate measured outcomes into bounded learning feedback.

    This engine changes learning confidence only.
    It never grants execution authority or modifies policy.
    """

    MAX_DELTA = 0.20
    BASE_REINFORCEMENT = 0.10
    FAILURE_PENALTY = 0.10

    def evaluate(
        self,
        *,
        status: OutcomeStatus,
        evidence: int,
        confidence: float,
        contradiction: bool = False,
    ) -> LearningFeedbackDecision:
        if not isinstance(status, OutcomeStatus):
            raise ValueError("status must be an OutcomeStatus")

        if isinstance(evidence, bool) or not isinstance(evidence, int):
            raise ValueError("evidence must be an integer")

        if evidence < 0:
            raise ValueError("evidence must not be negative")

        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError("confidence must be numeric")

        confidence = float(confidence)

        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        if not isinstance(contradiction, bool):
            raise ValueError("contradiction must be boolean")

        if status is OutcomeStatus.UNKNOWN:
            return LearningFeedbackDecision(
                strengthen=False,
                weaken=False,
                revalidate=False,
                confidence_delta=0.0,
                reason="unknown outcome does not modify learning",
            )

        if contradiction:
            return LearningFeedbackDecision(
                strengthen=False,
                weaken=True,
                revalidate=True,
                confidence_delta=-self.FAILURE_PENALTY,
                reason="contradictory outcome requires learning revalidation",
            )

        if status is OutcomeStatus.SUCCESS and evidence >= 1:
            delta = min(
                self.MAX_DELTA,
                self.BASE_REINFORCEMENT / sqrt(evidence + 1),
            )
            return LearningFeedbackDecision(
                strengthen=True,
                weaken=False,
                revalidate=False,
                confidence_delta=round(delta, 12),
                reason="successful evidence reinforces learned knowledge",
            )

        if status is OutcomeStatus.PARTIAL and evidence >= 1:
            delta = min(
                self.MAX_DELTA,
                (self.BASE_REINFORCEMENT * 0.5) / sqrt(evidence + 1),
            )
            return LearningFeedbackDecision(
                strengthen=True,
                weaken=False,
                revalidate=True,
                confidence_delta=round(delta, 12),
                reason="partial success provides limited reinforcement and requires revalidation",
            )

        if status is OutcomeStatus.FAILURE:
            return LearningFeedbackDecision(
                strengthen=False,
                weaken=True,
                revalidate=True,
                confidence_delta=-self.FAILURE_PENALTY,
                reason="failure challenges existing learning and requires revalidation",
            )

        return LearningFeedbackDecision(
            strengthen=False,
            weaken=False,
            revalidate=False,
            confidence_delta=0.0,
            reason="outcome did not provide actionable learning feedback",
        )
