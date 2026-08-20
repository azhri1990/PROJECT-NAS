"""Bounded fail-closed watchdog orchestration for PROJECT-BOB."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from runtime.bob_learning import FailureLesson, LearningLedger
from runtime.bob_supervisor import PersistentSupervisor


@dataclass(frozen=True)
class WatchdogDecision:
    action: str
    reason: str
    restart_allowed: bool


class BoundedWatchdog:
    """Turn supervisor health signals into bounded, deterministic actions."""

    def __init__(
        self,
        supervisor: PersistentSupervisor,
        *,
        max_restarts: int = 3,
        cooldown_seconds: float = 30.0,
        learning: LearningLedger | None = None,
    ) -> None:
        if max_restarts < 0:
            raise ValueError("max_restarts must be non-negative")
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        self.supervisor = supervisor
        self.max_restarts = max_restarts
        self.cooldown_seconds = cooldown_seconds
        self.learning = learning
        self._last_restart_at: float | None = None

    def inspect(self, *, now: float, timeout: float = 90.0) -> WatchdogDecision:
        if self.supervisor.state.status == "stopped":
            return WatchdogDecision("stop", "supervisor_stopped", False)

        action = self.supervisor.watchdog(now=now, timeout=timeout)
        if action == "healthy":
            return WatchdogDecision("continue", "heartbeat_fresh", False)

        failure_class = "heartbeat_timeout"
        if self.learning is not None and self.learning.should_escalate(failure_class):
            return WatchdogDecision("escalate", "known_failure_class", False)

        if self.supervisor.state.restart_count >= self.max_restarts:
            return WatchdogDecision("escalate", "restart_budget_exhausted", False)

        if self._last_restart_at is not None:
            elapsed = now - self._last_restart_at
            if elapsed < self.cooldown_seconds:
                return WatchdogDecision("wait", "restart_cooldown", False)

        return WatchdogDecision("restart", "heartbeat_timeout", True)

    def act(
        self,
        *,
        now: float,
        restart: Callable[[], Any],
        timeout: float = 90.0,
    ) -> WatchdogDecision:
        decision = self.inspect(now=now, timeout=timeout)
        if decision.action != "restart":
            return decision

        try:
            self.supervisor.request_restart(restart)
        except Exception as exc:
            if self.learning is not None:
                self.learning.record(
                    FailureLesson(
                        failure_class="heartbeat_timeout",
                        root_cause=f"restart failed: {type(exc).__name__}",
                        lesson="A heartbeat timeout can recur after a failed restart.",
                        prevention="Escalate known heartbeat-timeout failures before another automatic restart.",
                        regression="Watchdog must return escalate for a previously recorded heartbeat_timeout class.",
                    )
                )
            return WatchdogDecision("escalate", "restart_failed", False)

        self._last_restart_at = now
        return WatchdogDecision("restarted", "worker_restarted", False)
