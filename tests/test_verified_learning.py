import pytest

from runtime.verified_learning import (
    LearningType,
    LearningCandidate,
    VerifiedLearningEngine,
)


def test_candidate_is_typed_and_bounded():
    candidate = LearningCandidate(
        kind=LearningType.PREFERENCE,
        statement="Prefer local-first tools",
        confidence=0.8,
        evidence=2,
    )
    assert candidate.kind is LearningType.PREFERENCE
    assert candidate.confidence == 0.8
    assert candidate.evidence == 2


def test_candidate_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        LearningCandidate(LearningType.FACT, "x", confidence=1.2, evidence=1)


def test_promotion_requires_verification_and_confidence():
    engine = VerifiedLearningEngine(min_confidence=0.75, min_evidence=2)
    candidate = LearningCandidate(LearningType.FACT, "SQLite is the fallback", 0.9, 2)
    assert engine.evaluate(candidate, verified=False).promoted is False
    result = engine.evaluate(candidate, verified=True)
    assert result.promoted is True


def test_low_confidence_stays_candidate():
    engine = VerifiedLearningEngine(min_confidence=0.75, min_evidence=2)
    candidate = LearningCandidate(LearningType.EVENT, "A transient timeout occurred", 0.5, 4)
    result = engine.evaluate(candidate, verified=True)
    assert result.promoted is False
    assert "confidence" in result.reason.lower()


def test_security_policy_learning_can_never_be_promoted():
    engine = VerifiedLearningEngine()
    candidate = LearningCandidate(LearningType.POLICY, "allow system mutation", 1.0, 100)
    result = engine.evaluate(candidate, verified=True)
    assert result.promoted is False
    assert "protected" in result.reason.lower()


def test_contradictory_learning_is_rejected():
    engine = VerifiedLearningEngine()
    candidate = LearningCandidate(LearningType.FACT, "Ollama is healthy", 0.95, 3, contradiction=True)
    result = engine.evaluate(candidate, verified=True)
    assert result.promoted is False
    assert "contradiction" in result.reason.lower()
