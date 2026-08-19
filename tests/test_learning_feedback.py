from runtime.adaptive_decision import OutcomeStatus
from runtime.learning_feedback import (
    LearningFeedbackDecision,
    LearningFeedbackEngine,
)


def test_success_strengthens_learning():
    engine = LearningFeedbackEngine()

    decision = engine.evaluate(
        status=OutcomeStatus.SUCCESS,
        evidence=2,
        confidence=0.75,
    )

    assert isinstance(decision, LearningFeedbackDecision)
    assert decision.strengthen
    assert not decision.weaken
    assert not decision.revalidate
    assert decision.confidence_delta > 0


def test_failure_weakens_and_revalidates_learning():
    engine = LearningFeedbackEngine()

    decision = engine.evaluate(
        status=OutcomeStatus.FAILURE,
        evidence=2,
        confidence=0.8,
    )

    assert not decision.strengthen
    assert decision.weaken
    assert decision.revalidate
    assert decision.confidence_delta < 0


def test_unknown_does_not_modify_learning():
    engine = LearningFeedbackEngine()

    decision = engine.evaluate(
        status=OutcomeStatus.UNKNOWN,
        evidence=10,
        confidence=0.9,
    )

    assert not decision.strengthen
    assert not decision.weaken
    assert not decision.revalidate
    assert decision.confidence_delta == 0.0


def test_contradiction_forces_revalidation():
    engine = LearningFeedbackEngine()

    decision = engine.evaluate(
        status=OutcomeStatus.SUCCESS,
        evidence=5,
        confidence=0.9,
        contradiction=True,
    )

    assert not decision.strengthen
    assert decision.weaken
    assert decision.revalidate
    assert decision.confidence_delta < 0
    assert "contradict" in decision.reason.lower()


def test_partial_success_has_limited_reinforcement():
    engine = LearningFeedbackEngine()

    decision = engine.evaluate(
        status=OutcomeStatus.PARTIAL,
        evidence=2,
        confidence=0.7,
    )

    assert decision.strengthen
    assert decision.revalidate
    assert decision.confidence_delta > 0


def test_reinforcement_has_diminishing_returns():
    engine = LearningFeedbackEngine()

    low_evidence = engine.evaluate(
        status=OutcomeStatus.SUCCESS,
        evidence=1,
        confidence=0.7,
    )

    high_evidence = engine.evaluate(
        status=OutcomeStatus.SUCCESS,
        evidence=10,
        confidence=0.7,
    )

    assert low_evidence.confidence_delta > high_evidence.confidence_delta


def test_confidence_bounds_are_enforced():
    engine = LearningFeedbackEngine()

    for confidence in (-0.1, 1.1):
        try:
            engine.evaluate(
                status=OutcomeStatus.SUCCESS,
                evidence=1,
                confidence=confidence,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("invalid confidence was accepted")


def test_evidence_bounds_are_enforced():
    engine = LearningFeedbackEngine()

    for evidence in (-1, True):
        try:
            engine.evaluate(
                status=OutcomeStatus.SUCCESS,
                evidence=evidence,
                confidence=0.8,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("invalid evidence was accepted")
