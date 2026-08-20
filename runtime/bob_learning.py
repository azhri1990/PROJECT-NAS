"""Failure-learning adapter connecting PROJECT-BOB to the NAS learning loop."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from runtime.adaptive_decision import OutcomeStatus


@dataclass(frozen=True)
class FailureDecision:
    action: str
    failure_count: int


class BobFailureLearner:
    """Persist BOB failures and escalate repeated failures instead of looping."""

    def __init__(self, loop: Any, *, failure_threshold: int = 2) -> None:
        if not isinstance(failure_threshold, int) or isinstance(failure_threshold, bool) or failure_threshold < 1:
            raise ValueError("failure_threshold must be a positive integer")
        self.loop = loop
        self.failure_threshold = failure_threshold

    def observe_failure(
        self,
        *,
        task: str,
        strategy_id: str,
        context: str,
        source: str,
        lesson: str,
    ) -> FailureDecision:
        observation_id = self.loop.observe(task, strategy_id, context, source)
        self.loop.record_outcome(
            observation_id,
            OutcomeStatus.FAILURE,
            evidence=1,
            lesson=lesson,
        )
        failure_count = self.loop.failure_count(strategy_id)
        action = "ESCALATE" if failure_count >= self.failure_threshold else "RETRY"
        return FailureDecision(action, failure_count)
