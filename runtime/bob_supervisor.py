"""Persistent, policy-neutral supervisor state machine for PROJECT-BOB workers.

The supervisor owns lifecycle/recovery state only. It does not execute commands,
spawn shells, or grant authorization. Actual execution remains behind BOB/NAS
policy boundaries.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import time
from typing import Any, Callable


@dataclass
class SupervisorState:
    worker_id: str
    status: str = "starting"
    last_heartbeat: float | None = None
    restart_count: int = 0
    reconnect_count: int = 0
    recovered_jobs: int = 0
    updated_at: float = field(default_factory=time.time)


class PersistentSupervisor:
    """Crash-safe lifecycle state with deterministic watchdog decisions."""

    VALID_STATUSES = {"starting", "ready", "offline", "stopping", "stopped"}

    def __init__(self, worker_id: str, state_path: str | Path):
        if not worker_id.strip():
            raise ValueError("worker_id must not be empty")
        self.state_path = Path(state_path)
        self.state = self._load(worker_id)

    def _load(self, worker_id: str) -> SupervisorState:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return SupervisorState(worker_id=worker_id)
        if data.get("worker_id") != worker_id:
            raise ValueError("persisted worker identity does not match")
        status = data.get("status", "starting")
        if status not in self.VALID_STATUSES:
            raise ValueError("invalid persisted supervisor status")
        return SupervisorState(**{k: data[k] for k in SupervisorState.__dataclass_fields__ if k in data})

    def persist(self) -> None:
        self.state.updated_at = time.time()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(asdict(self.state), sort_keys=True), encoding="utf-8")
        tmp.replace(self.state_path)

    def start(self) -> None:
        self.state.status = "ready"
        self.persist()

    def heartbeat(self, now: float | None = None) -> None:
        now = time.time() if now is None else now
        self.state.last_heartbeat = now
        self.state.status = "ready"
        self.persist()

    def watchdog(self, now: float | None = None, timeout: float = 90.0) -> str:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        now = time.time() if now is None else now
        if self.state.last_heartbeat is None or now - self.state.last_heartbeat > timeout:
            self.state.status = "offline"
            self.persist()
            return "reconnect"
        return "healthy"

    def reconnect(self) -> None:
        self.state.reconnect_count += 1
        self.state.status = "ready"
        self.persist()

    def record_recovered_jobs(self, count: int) -> None:
        if count < 0:
            raise ValueError("count must be non-negative")
        self.state.recovered_jobs += count
        self.persist()

    def request_restart(self, restart: Callable[[], Any]) -> Any:
        if self.state.status == "stopped":
            raise RuntimeError("cannot restart a stopped supervisor")
        self.state.restart_count += 1
        self.state.status = "starting"
        self.persist()
        try:
            result = restart()
        except Exception:
            self.state.status = "offline"
            self.persist()
            raise
        self.state.status = "ready"
        self.persist()
        return result

    def stop(self) -> None:
        self.state.status = "stopping"
        self.persist()
        self.state.status = "stopped"
        self.persist()
