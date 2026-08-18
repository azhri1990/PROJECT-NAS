"""Deterministic learning-quality calibration for JARVIS/PROJECT-NAS."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LearningQualityDecision:
    promote: bool
    confidence: float
    quality_score: float
    stale: bool
    reason: str


class LearningQualityEngine:
    """Score learning evidence without granting policy or capability authority."""

    MIN_EVIDENCE = 2
    MIN_QUALITY = 0.70
    STALE_THRESHOLD = 0.50
    CONTRADICTION_PENALTY = 0.25
    UNVERIFIED_PENALTY = 0.35

    @staticmethod
    def _confidence(value: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("confidence must be numeric")
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return float(value)

    @staticmethod
    def _evidence(value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("evidence must be a non-negative integer")
        return value

    def evaluate(
        self,
        *,
        confidence: float,
        evidence: int,
        verified: bool,
        contradiction: bool,
    ) -> LearningQualityDecision:
        confidence = self._confidence(confidence)
        evidence = self._evidence(evidence)
        if not isinstance(verified, bool) or not isinstance(contradiction, bool):
            raise ValueError("verified and contradiction must be boolean")

        evidence_score = min(1.0, evidence / float(self.MIN_EVIDENCE))
        quality = confidence * 0.60 + evidence_score * 0.40
        if not verified:
            quality -= self.UNVERIFIED_PENALTY
        if contradiction:
            quality -= self.CONTRADICTION_PENALTY
            confidence = max(0.0, confidence - self.CONTRADICTION_PENALTY)
        quality = max(0.0, min(1.0, quality))

        stale = self.is_stale(confidence)
        if contradiction:
            reason = "learning rejected because contradiction requires revalidation"
        elif not verified:
            reason = "learning rejected because verification is required"
        elif evidence < self.MIN_EVIDENCE:
            reason = "learning rejected because evidence is below threshold"
        elif quality < self.MIN_QUALITY:
            reason = "learning rejected because calibrated quality is below threshold"
        elif stale:
            reason = "learning rejected because confidence is stale"
        else:
            reason = "learning quality passed calibrated evidence and confidence gates"

        return LearningQualityDecision(
            promote=quality >= self.MIN_QUALITY and evidence >= self.MIN_EVIDENCE and verified and not contradiction and not stale,
            confidence=confidence,
            quality_score=quality,
            stale=stale,
            reason=reason,
        )

    def decay_confidence(self, confidence: float, *, decay: float = 0.05, floor: float = 0.0) -> float:
        confidence = self._confidence(confidence)
        decay = self._confidence(decay)
        floor = self._confidence(floor)
        if floor > confidence:
            raise ValueError("floor must not exceed confidence")
        return max(floor, confidence - decay)

    def is_stale(self, confidence: float) -> bool:
        return self._confidence(confidence) < self.STALE_THRESHOLD
