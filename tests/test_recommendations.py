from runtime.recommendations import Recommendation, RecommendationEngine


def test_recommendation_is_advisory_only():
    recommendation = RecommendationEngine().build(
        title="Use a local model",
        explanation="Avoids paid API dependency.",
        benefit="Keeps the runtime at zero recurring API cost.",
        risk="low",
        alternatives=("Use a hosted model",),
    )

    assert isinstance(recommendation, Recommendation)
    assert recommendation.title == "Use a local model"
    assert recommendation.requires_approval is False
    assert recommendation.authorizes_execution is False


def test_recommendation_rejects_empty_reasoning():
    try:
        RecommendationEngine().build(
            title="Better approach",
            explanation="",
            benefit="Some benefit",
            risk="low",
        )
    except ValueError as exc:
        assert "explanation" in str(exc)
    else:
        raise AssertionError("empty explanation must be rejected")
