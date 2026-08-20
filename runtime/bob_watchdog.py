"""Bounded fail-closed watchdog orchestration for PROJECT-BOB.

The watchdog coordinates lifecycle decisions only. It never executes commands
itself and never expands worker authority. Actual restart behavior is supplied
by the caller and remains subject to the existing BOB/NAS policy boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

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
    ) -> None:
        if max_restarts < 0:
            raise ValueError("max_restarts must be non-negative")
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        self.supervisor = supervisor
        self.max_restarts = max_restarts
        self.cooldown_seconds = cooldown_seconds
        self._last_restart_at: float | None = None

    def inspect(self, *, now: float, timeout: float = 90.0) -> WatchdogDecision:
        if self.supervisor.state.status == "stopped":
            return WatchdogDecision("stop", "supervisor_stopped", False)

        action = self.supervisor.watchdog(now=now, timeout=timeout)
        if action == "healthy":
            return WatchdogDecision("continue", "heartbeat_fresh", False)

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
        except Exception:
            # Supervisor persists OFFLINE on restart failure. Do not retry
            # recursively or bypass the restart budget in this call.
            return WatchdogDecision("escalate", "restart_failed", False)

        self._last_restart_at = now
        return WatchdogDecision("restarted", "worker_restarted", False)
