"""Conservative outcome feedback for adaptive strategy learning."""

from __future__ import annotations

from runtime.adaptive_decision import AdaptiveDecisionEngine, OutcomeStatus
from runtime.strategy_memory import StrategyMemory


class OutcomeFeedback:
    def __init__(self, memory: StrategyMemory, engine: AdaptiveDecisionEngine) -> None:
        self.memory = memory
        self.engine = engine

    def record(self, strategy_id: str, status: OutcomeStatus) -> None:
        self.memory.record_outcome(strategy_id, status)
        self.engine.observe(strategy_id, status)

    def apply(self, strategy_id: str, status: OutcomeStatus) -> None:
        self.record(strategy_id, status)

    def strategy_effect(self, strategy_id: str):
        return self.memory.strategy_stats(strategy_id)
