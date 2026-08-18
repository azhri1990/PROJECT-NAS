from pathlib import Path

import pytest

from runtime.adaptive_decision import AdaptiveDecisionEngine, DecisionCandidate, DecisionContext, StrategyOutcome, OutcomeStatus, Strategy


def test_strategy_identity_is_deterministic_and_fields_are_bounded():
    a = Strategy("local-memory", "Use verified local memory", risk=0.2, cost=0.1)
    b = Strategy("local-memory", "Use verified local memory", risk=0.2, cost=0.1)
    assert a.id == b.id
    with pytest.raises(ValueError):
        Strategy("bad", "x", risk=1.1, cost=0.1)


def test_outcome_and_candidate_validate():
    strategy = Strategy("local", "local strategy")
    assert StrategyOutcome(strategy.id, OutcomeStatus.SUCCESS).status is OutcomeStatus.SUCCESS
    with pytest.raises(ValueError):
        DecisionCandidate(strategy, confidence=1.2)


def test_rank_prefers_high_success_strategy():
    strong = Strategy("strong", "strong strategy", risk=0.1, cost=0.1)
    weak = Strategy("weak", "weak strategy", risk=0.5, cost=0.8)
    engine = AdaptiveDecisionEngine()
    engine.observe(strong.id, OutcomeStatus.SUCCESS)
    engine.observe(strong.id, OutcomeStatus.SUCCESS)
    engine.observe(weak.id, OutcomeStatus.FAILURE)
    ranked = engine.rank([DecisionCandidate(weak, 0.7), DecisionCandidate(strong, 0.7)], DecisionContext())
    assert ranked[0].strategy.id == strong.id


def test_unknown_outcome_does_not_change_success_rate():
    strategy = Strategy("stable", "stable strategy")
    engine = AdaptiveDecisionEngine()
    engine.observe(strategy.id, OutcomeStatus.SUCCESS)
    before = engine.stats(strategy.id)
    engine.observe(strategy.id, OutcomeStatus.UNKNOWN)
    after = engine.stats(strategy.id)
    assert after.success_rate == before.success_rate
    assert after.observations == before.observations
