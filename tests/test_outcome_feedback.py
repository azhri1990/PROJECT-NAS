from pathlib import Path

from runtime.adaptive_decision import AdaptiveDecisionEngine, OutcomeStatus, Strategy
from runtime.outcome_feedback import OutcomeFeedback
from runtime.strategy_memory import StrategyMemory


def test_feedback_updates_persistent_and_runtime_stats(tmp_path: Path):
    memory = StrategyMemory(tmp_path / "strategy.sqlite3")
    engine = AdaptiveDecisionEngine()
    feedback = OutcomeFeedback(memory, engine)
    strategy = Strategy("feedback", "feedback strategy")
    memory.record_strategy(strategy)
    feedback.record(strategy.id, OutcomeStatus.SUCCESS)
    feedback.record(strategy.id, OutcomeStatus.PARTIAL)
    assert feedback.strategy_effect(strategy.id).observations == 2
    assert engine.stats(strategy.id).partial_rate == 0.5


def test_unknown_feedback_has_no_learning_effect(tmp_path: Path):
    memory = StrategyMemory(tmp_path / "strategy.sqlite3")
    engine = AdaptiveDecisionEngine()
    feedback = OutcomeFeedback(memory, engine)
    strategy = Strategy("unknown", "unknown feedback")
    memory.record_strategy(strategy)
    feedback.record(strategy.id, OutcomeStatus.UNKNOWN)
    assert feedback.strategy_effect(strategy.id).observations == 0
    assert engine.stats(strategy.id).observations == 0
