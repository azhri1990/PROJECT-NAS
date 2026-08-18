from pathlib import Path

from runtime.adaptive_decision import OutcomeStatus, Strategy
from runtime.strategy_memory import StrategyMemory


def test_strategy_memory_resolves_registered_strategy_name_to_id(tmp_path: Path):
    memory = StrategyMemory(tmp_path / "strategy_memory.sqlite3")
    strategy = Strategy("local", "local verified path", risk=0.1, cost=0.1)
    memory.record_strategy(strategy)

    assert memory.resolve_strategy_id("local") == strategy.id
    assert memory.resolve_strategy_id(strategy.id) == strategy.id

    memory.record_outcome("local", OutcomeStatus.SUCCESS)
    assert memory.strategy_stats("local").success_rate == 1.0


def test_unknown_strategy_still_fails_closed(tmp_path: Path):
    memory = StrategyMemory(tmp_path / "strategy_memory.sqlite3")
    try:
        memory.record_outcome("missing", OutcomeStatus.SUCCESS)
    except KeyError as exc:
        assert "strategy not found" in str(exc).lower()
    else:
        raise AssertionError("unknown strategy was accepted")
