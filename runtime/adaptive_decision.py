"""Deterministic adaptive decision scoring for PROJECT-NAS.

Learning changes ranking and confidence only; it never grants execution authority.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum


class OutcomeStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Strategy:
    name: str
    description: str
    risk: float = 0.0
    cost: float = 0.0

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.description.strip():
            raise ValueError("strategy name and description must not be empty")
        if not 0.0 <= self.risk <= 1.0:
            raise ValueError("strategy risk must be between 0 and 1")
        if not 0.0 <= self.cost <= 1.0:
            raise ValueError("strategy cost must be between 0 and 1")

    @property
    def id(self) -> str:
        return hashlib.sha256(self.name.strip().lower().encode()).hexdigest()[:16]


@dataclass(frozen=True)
class StrategyOutcome:
    strategy_id: str
    status: OutcomeStatus


@dataclass(frozen=True)
class DecisionCandidate:
    strategy: Strategy
    confidence: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("candidate confidence must be between 0 and 1")


@dataclass(frozen=True)
class DecisionContext:
    resource_pressure: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.resource_pressure <= 1.0:
            raise ValueError("resource pressure must be between 0 and 1")


@dataclass(frozen=True)
class StrategyStats:
    observations: int = 0
    success_rate: float = 0.5
    partial_rate: float = 0.0
    failure_rate: float = 0.0


@dataclass(frozen=True)
class DecisionScore:
    strategy: Strategy
    score: float
    success_rate: float


class AdaptiveDecisionEngine:
    """Rank strategies using confidence, outcomes, risk and local resource cost."""

    def __init__(self) -> None:
        self._stats: dict[str, StrategyStats] = {}

    def observe(self, strategy_id: str, status: OutcomeStatus) -> None:
        if not strategy_id.strip():
            raise ValueError("strategy_id must not be empty")
        if status is OutcomeStatus.UNKNOWN:
            return
        current = self._stats.get(strategy_id, StrategyStats())
        total = current.observations + 1
        success = current.success_rate * current.observations
        partial = current.partial_rate * current.observations
        failure = current.failure_rate * current.observations
        if status is OutcomeStatus.SUCCESS:
            success += 1
        elif status is OutcomeStatus.PARTIAL:
            partial += 1
        elif status is OutcomeStatus.FAILURE:
            failure += 1
        self._stats[strategy_id] = StrategyStats(
            observations=total,
            success_rate=success / total,
            partial_rate=partial / total,
            failure_rate=failure / total,
        )

    def stats(self, strategy_id: str) -> StrategyStats:
        return self._stats.get(strategy_id, StrategyStats())

    def rank(self, candidates: list[DecisionCandidate], context: DecisionContext | None = None) -> list[DecisionScore]:
        if not isinstance(candidates, list):
            raise ValueError("candidates must be a list")
        if len(candidates) > 50:
            raise ValueError("candidates must contain at most 50 items")
        context = context or DecisionContext()
        scored: list[DecisionScore] = []
        for candidate in candidates:
            stats = self.stats(candidate.strategy.id)
            empirical = stats.success_rate + stats.partial_rate * 0.5
            risk_penalty = candidate.strategy.risk * (0.20 + context.resource_pressure * 0.10)
            cost_penalty = candidate.strategy.cost * (0.10 + context.resource_pressure * 0.25)
            score = candidate.confidence * 0.55 + empirical * 0.35 - risk_penalty - cost_penalty
            scored.append(DecisionScore(candidate.strategy, max(0.0, min(1.0, score)), stats.success_rate))
        scored.sort(key=lambda item: (-item.score, -item.success_rate, item.strategy.id))
        return scored
