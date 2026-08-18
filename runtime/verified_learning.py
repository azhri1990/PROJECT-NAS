"""Deterministic, zero-cost continual-learning contracts for PROJECT-NAS."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LearningType(str, Enum):
    FACT = "FACT"
    EVENT = "EVENT"
    PREFERENCE = "PREFERENCE"
    DECISION = "DECISION"
    TASK = "TASK"
    SYSTEM_STATE = "SYSTEM_STATE"
    POLICY = "POLICY"


@dataclass(frozen=True)
class LearningCandidate:
    kind: LearningType
    statement: str
    confidence: float
    evidence: int
    contradiction: bool = False

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise ValueError("learning statement must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("learning confidence must be between 0 and 1")
        if self.evidence < 0:
            raise ValueError("learning evidence must not be negative")


@dataclass(frozen=True)
class LearningDecision:
    promoted: bool
    reason: str


class VerifiedLearningEngine:
    """Promotes only verified, sufficiently supported, non-protected learning."""

    _PROTECTED = {LearningType.POLICY}

    def __init__(self, min_confidence: float = 0.75, min_evidence: int = 2) -> None:
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")
        if min_evidence < 1:
            raise ValueError("min_evidence must be at least 1")
        self.min_confidence = min_confidence
        self.min_evidence = min_evidence

    def evaluate(self, candidate: LearningCandidate, *, verified: bool) -> LearningDecision:
        if candidate.kind in self._PROTECTED:
            return LearningDecision(False, "protected policy learning cannot be promoted automatically")
        if candidate.contradiction:
            return LearningDecision(False, "learning candidate contains a contradiction")
        if not verified:
            return LearningDecision(False, "learning candidate requires verification")
        if candidate.confidence < self.min_confidence:
            return LearningDecision(False, "learning candidate confidence is below threshold")
        if candidate.evidence < self.min_evidence:
            return LearningDecision(False, "learning candidate evidence is below threshold")
        return LearningDecision(True, "verified learning candidate promoted")
