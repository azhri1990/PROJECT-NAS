from pathlib import Path

from runtime.adaptive_decision import Strategy, DecisionCandidate, DecisionContext, OutcomeStatus
from runtime.second_brain import SecondBrain


def test_second_brain_strategy_feedback_improves_future_ranking(tmp_path: Path):
    brain = SecondBrain(tmp_path / "brain.sqlite3")
    fast = Strategy("fast", "cheap local path", risk=0.2, cost=0.1)
    safe = Strategy("safe", "verified conservative path", risk=0.1, cost=0.2)
    brain.record_strategy(fast)
    brain.record_strategy(safe)
    brain.record_outcome(fast.id, OutcomeStatus.FAILURE)
    brain.record_outcome(fast.id, OutcomeStatus.FAILURE)
    brain.record_outcome(safe.id, OutcomeStatus.SUCCESS)
    brain.record_outcome(safe.id, OutcomeStatus.SUCCESS)

    ranked = brain.recommend_strategy([DecisionCandidate(fast, 0.8), DecisionCandidate(safe, 0.8)], DecisionContext())
    assert ranked[0].strategy.id == safe.id


def test_unknown_outcome_does_not_train_strategy(tmp_path: Path):
    brain = SecondBrain(tmp_path / "brain.sqlite3")
    strategy = Strategy("unknown", "unknown result")
    brain.record_strategy(strategy)
    before = brain.strategy_history(strategy.id)
    brain.record_outcome(strategy.id, OutcomeStatus.UNKNOWN)
    after = brain.strategy_history(strategy.id)
    assert after == before
