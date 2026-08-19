"""Authenticated, policy-gated command service for PROJECT-BOB."""

from __future__ import annotations

import importlib
import threading
from typing import Any

from runtime.policy import Capability, PolicyEngine, RiskLevel, ToolRequest

_bob_queue = importlib.import_module("07-AUTOMATION.bob.job_queue")
_bob_devices = importlib.import_module("07-AUTOMATION.bob.device_registry")
_bob_router = importlib.import_module("07-AUTOMATION.bob.task_router")

JobQueue = _bob_queue.JobQueue
JobState = _bob_queue.JobState
Device = _bob_devices.Device
DeviceRegistry = _bob_devices.DeviceRegistry
TaskRouter = _bob_router.TaskRouter


class BobCommandService:
    """Bounded command lifecycle; execution authority remains outside BOB."""

    def __init__(self, *, policy: PolicyEngine | None = None, audit_limit: int = 200) -> None:
        if audit_limit < 1:
            raise ValueError("audit_limit must be positive")
        self.queue = JobQueue()
        self.devices = DeviceRegistry()
        self.router = TaskRouter(self.devices, self.queue)
        self.policy = policy or PolicyEngine()
        self.audit: list[dict[str, Any]] = []
        self._audit_limit = audit_limit
        self._lock = threading.RLock()

    def _record(self, event: str, **data: Any) -> None:
        self.audit.append({"event": event, **data})
        if len(self.audit) > self._audit_limit:
            del self.audit[: len(self.audit) - self._audit_limit]

    @staticmethod
    def _capability(value: str) -> Capability:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("capability must be a non-empty string")
        try:
            return Capability(value.strip())
        except ValueError as exc:
            raise ValueError(f"unknown capability: {value}") from exc

    def submit(self, *, task: str, capability: str) -> dict[str, Any]:
        if not isinstance(task, str) or not task.strip() or len(task.strip()) > 4000:
            raise ValueError("task must be a non-empty string of at most 4000 characters")
        with self._lock:
            cap = self._capability(capability)
            request = ToolRequest(
                tool_name=f"bob.job.{cap.value}",
                capability=cap,
                risk=RiskLevel.LOW,
                input={"task": task.strip()},
            )
            decision = self.policy.evaluate(request)
            self._record("policy", allowed=decision.allowed, capability=cap.value, reason=decision.reason)
            if not decision.allowed:
                raise PermissionError(decision.reason)
            job = self.queue.create(task, cap.value)
            self.queue.update(job.job_id, state=JobState.QUEUED)
            route = self.router.route(self.queue.get(job.job_id))
            self._record("submit", job_id=job.job_id, state=route.state.value, worker_id=route.worker_id)
            return self._job(self.queue.get(job.job_id))

    def status(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self.queue.get(job_id)
            if job is None:
                raise KeyError(job_id)
            return self._job(job)

    def cancel(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            try:
                updated = self.queue.cancel(job_id)
            except KeyError as exc:
                raise KeyError(job_id) from exc
            self._record("cancel", job_id=job_id)
            return self._job(updated)

    def heartbeat(self, *, device_id: str, platform: str, capabilities: list[str], online: bool = True, cost: float = 0.0) -> dict[str, Any]:
        if not isinstance(device_id, str) or not device_id.strip() or not isinstance(platform, str) or not platform.strip():
            raise ValueError("device_id and platform must be non-empty strings")
        if not isinstance(capabilities, list) or len(capabilities) > 32 or any(not isinstance(item, str) or not item.strip() for item in capabilities):
            raise ValueError("capabilities must be a list of at most 32 non-empty strings")
        if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
            raise ValueError("cost must be a non-negative number")
        with self._lock:
            normalized = [item.strip() for item in capabilities]
            self.devices.register(Device(device_id=device_id.strip(), platform=platform.strip(), capabilities=frozenset(normalized), online=bool(online), cost=float(cost)))
            self._record("heartbeat", device_id=device_id.strip(), online=bool(online))
            return self.worker(device_id.strip())

    def worker(self, device_id: str) -> dict[str, Any]:
        device = self.devices.get(device_id)
        if device is None:
            raise KeyError(device_id)
        return {"device_id": device.device_id, "platform": device.platform, "capabilities": sorted(device.capabilities), "online": device.online, "cost": device.cost, "last_seen": self.devices.last_seen(device.device_id)}

    def workers(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self.worker(device.device_id) for device in self.devices.all()]

    @staticmethod
    def _job(job: Any) -> dict[str, Any]:
        if job is None:
            raise KeyError("job")
        return {"job_id": job.job_id, "task": job.task, "capability": job.capability, "state": job.state.value, "worker_id": job.worker_id, "reason": job.reason}