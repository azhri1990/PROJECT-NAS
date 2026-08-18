from pathlib import Path

from runtime.adaptive_decision import OutcomeStatus, Strategy
from runtime.strategy_memory import StrategyMemory


def test_strategy_memory_persists_strategy_and_outcomes(tmp_path: Path):
    path = tmp_path / "strategy.sqlite3"
    strategy = Strategy("persist", "persistent strategy")
    memory = StrategyMemory(path)
    memory.record_strategy(strategy)
    memory.record_outcome(strategy.id, OutcomeStatus.SUCCESS)
    memory.record_outcome(strategy.id, OutcomeStatus.FAILURE)
    reopened = StrategyMemory(path)
    assert reopened.list_strategies()[0].id == strategy.id
    stats = reopened.strategy_stats(strategy.id)
    assert stats.observations == 2
    assert stats.success_rate == 0.5


def test_unknown_outcome_is_not_persisted(tmp_path: Path):
    strategy = Strategy("unknown", "unknown strategy")
    memory = StrategyMemory(tmp_path / "strategy.sqlite3")
    memory.record_strategy(strategy)
    memory.record_outcome(strategy.id, OutcomeStatus.UNKNOWN)
    assert memory.outcomes(strategy.id) == []
