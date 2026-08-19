"""Android/Termux client for the authenticated PROJECT-BOB worker protocol.

The client contains no shell endpoint and accepts only already-authorized job
leases from BOB. Execution is deliberately represented by a caller-supplied
safe handler rather than arbitrary command strings.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

from .android_state import AndroidState
from .worker_protocol import JobResult, Platform, WorkerRegistration


@dataclass(frozen=True)
class AndroidWorkerConfig:
    worker_id: str
    endpoint: str
    auth_token: str
    capabilities: frozenset[str] = field(default_factory=frozenset)
    resources: dict[str, float] = field(default_factory=dict)
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not self.worker_id.strip():
            raise ValueError("worker_id must not be empty")
        if not self.endpoint.startswith(("http://", "https://")):
            raise ValueError("endpoint must be an HTTP(S) URL")
        if not self.auth_token.strip():
            raise ValueError("auth_token must not be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


class AndroidWorker:
    def __init__(self, config: AndroidWorkerConfig, state: AndroidState, opener: Callable[..., Any] | None = None):
        self.config = config
        self.state = state
        self._opener = opener or urllib.request.urlopen
        self.registered = False

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.config.endpoint.rstrip("/") + path,
            data=body,
            method=method,
            headers={"Authorization": f"Bearer {self.config.auth_token}", "Content-Type": "application/json"},
        )
        with self._opener(request, timeout=self.config.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def register(self, now: float | None = None) -> dict[str, Any]:
        payload = {
            "worker_id": self.config.worker_id,
            "platform": "android",
            "capabilities": sorted(self.config.capabilities),
            "resources": dict(self.config.resources),
            "now": time.time() if now is None else now,
        }
        result = self._request("POST", "/workers/register", payload)
        self.registered = True
        return result

    def heartbeat(self, now: float | None = None) -> dict[str, Any]:
        if not self.registered:
            raise RuntimeError("worker must register before heartbeat")
        return self._request("POST", "/workers/heartbeat", {
            "worker_id": self.config.worker_id,
            "now": time.time() if now is None else now,
            "resources": dict(self.config.resources),
        })

    def claim(self, job_id: str, capability: str, now: float | None = None) -> dict[str, Any]:
        if capability not in self.config.capabilities:
            raise PermissionError("worker does not advertise requested capability")
        if not self.registered:
            raise RuntimeError("worker must register before claiming jobs")
        return self._request("POST", "/jobs/claim", {
            "job_id": job_id,
            "worker_id": self.config.worker_id,
            "capability": capability,
            "now": time.time() if now is None else now,
        })

    def report_result(self, job_id: str, lease_id: str, status: str, output: dict[str, Any], now: float | None = None) -> dict[str, Any]:
        if status not in {"succeeded", "failed", "cancelled"}:
            raise ValueError("unsupported result status")
        payload = {"job_id": job_id, "lease_id": lease_id, "worker_id": self.config.worker_id, "status": status, "output": dict(output), "now": time.time() if now is None else now}
        self.state.queue_result(lease_id, payload)
        try:
            result = self._request("POST", "/jobs/result", payload)
        except (urllib.error.URLError, TimeoutError, OSError):
            raise
        self.state.remove_result(lease_id)
        return result

    def flush_results(self) -> list[str]:
        flushed: list[str] = []
        pending = self.state.load()["pending_results"]
        for lease_id, payload in list(pending.items()):
            try:
                self._request("POST", "/jobs/result", payload)
            except (urllib.error.URLError, TimeoutError, OSError):
                continue
            self.state.remove_result(lease_id)
            flushed.append(lease_id)
        return flushed


__all__ = ["AndroidWorker", "AndroidWorkerConfig", "Platform", "WorkerRegistration", "JobResult"]
