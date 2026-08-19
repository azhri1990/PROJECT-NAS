from runtime.learning_quality import LearningQualityEngine, LearningQualityDecision


def test_quality_requires_evidence_and_verification():
    engine = LearningQualityEngine()
    decision = engine.evaluate(confidence=0.8, evidence=1, verified=True, contradiction=False)
    assert not decision.promote
    assert "evidence" in decision.reason.lower()


def test_quality_reduces_confidence_for_conflict():
    engine = LearningQualityEngine()
    decision = engine.evaluate(confidence=0.9, evidence=3, verified=True, contradiction=True)
    assert not decision.promote
    assert decision.confidence < 0.9
    assert "contradiction" in decision.reason.lower()


def test_quality_promotes_strong_evidence():
    engine = LearningQualityEngine()
    decision = engine.evaluate(confidence=0.9, evidence=3, verified=True, contradiction=False)
    assert isinstance(decision, LearningQualityDecision)
    assert decision.promote
    assert decision.confidence >= 0.9


def test_quality_decay_marks_stale_when_confidence_falls():
    engine = LearningQualityEngine()
    assert engine.decay_confidence(0.54, decay=0.1, floor=0.0) == 0.44
    assert engine.is_stale(0.44)


def test_quality_bounds_inputs():
    engine = LearningQualityEngine()
    for kwargs in (
        {"confidence": 1.1, "evidence": 2, "verified": True, "contradiction": False},
        {"confidence": 0.8, "evidence": -1, "verified": True, "contradiction": False},
    ):
        try:
            engine.evaluate(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid learning-quality input was accepted")
