"""Authenticated HTTP worker service for PROJECT-BOB.

This module exposes worker lifecycle and lease operations only. It deliberately
contains no arbitrary shell or command-execution endpoint.
"""
from __future__ import annotations

import os
from typing import Any

from runtime.policy import Capability, PolicyEngine, RiskLevel, ToolRequest

from .audit import WorkerAudit
from .job_lease import JobLeaseStore
from .worker_protocol import JobResult, WorkerRegistration
from .worker_registry import WorkerRegistry

try:
    from fastapi import FastAPI, Header, HTTPException
except ImportError:  # pragma: no cover
    FastAPI = None  # type: ignore[assignment]


def _auth_identity(authorization: str | None, expected: str | None) -> str:
    if not expected:
        raise RuntimeError("worker authentication is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise PermissionError("authentication required")
    if authorization[7:].strip() != expected:
        raise PermissionError("invalid authentication token")
    return "authenticated-worker"


_CAPABILITY_MAP = {
    "read_repository": Capability.READ_REPOSITORY,
    "read_runtime": Capability.READ_RUNTIME,
    "write_repository": Capability.WRITE_REPOSITORY,
    "execute_process": Capability.EXECUTE_PROCESS,
    "network_access": Capability.NETWORK_ACCESS,
}


class WorkerService:
    def __init__(self, registry: WorkerRegistry, leases: JobLeaseStore, audit: WorkerAudit | None = None, auth_token: str | None = None, policy: PolicyEngine | None = None) -> None:
        self.registry = registry
        self.leases = leases
        self.audit = audit or WorkerAudit()
        self.auth_token = auth_token if auth_token is not None else os.getenv("PROJECT_BOB_AUTH_TOKEN")
        self.policy = policy or PolicyEngine()

    def register(self, registration: WorkerRegistration, now: float = 0.0) -> dict[str, Any]:
        record = self.registry.register_worker(registration, now=now)
        self.audit.record("worker_registered", record.worker_id, details={"platform": record.platform})
        return {"worker_id": record.worker_id, "status": record.status, "platform": record.platform, "capabilities": sorted(record.capabilities)}

    def heartbeat(self, worker_id: str, identity: str, now: float, resources: dict[str, float] | None = None) -> dict[str, Any]:
        record = self.registry.heartbeat(worker_id, identity, now, resources)
        self.audit.record("worker_heartbeat", worker_id)
        return {"worker_id": record.worker_id, "status": record.status, "last_seen": record.last_seen}

    def claim(self, job_id: str, worker_id: str, capability: str, now: float) -> dict[str, Any]:
        worker = self.registry.get(worker_id)
        if worker is None or worker.status != "available":
            raise PermissionError("worker is not registered and available")
        if not worker.supports(capability):
            raise PermissionError("worker does not advertise required capability")
        policy_capability = _CAPABILITY_MAP.get(capability)
        if policy_capability is None:
            self.audit.record("job_denied", worker_id, job_id, {"reason": "unknown capability"})
            raise PermissionError("unknown capability denied by NAS policy")
        decision = self.policy.evaluate(ToolRequest("bob.worker.claim", policy_capability, RiskLevel.LOW, {"job_id": job_id, "worker_id": worker_id}))
        if not decision.allowed:
            self.audit.record("job_denied", worker_id, job_id, {"reason": decision.reason})
            raise PermissionError(decision.reason)
        lease = self.leases.claim(job_id, worker_id, now)
        self.audit.record("job_claimed", worker_id, job_id, {"lease_id": lease.lease_id})
        return {"job_id": lease.job_id, "lease_id": lease.lease_id, "expires_at": lease.expires_at}

    def result(self, worker_id: str, result: JobResult, now: float) -> dict[str, Any]:
        completion = self.leases.complete(result.lease_id, worker_id, result, now)
        self.audit.record("job_completed", worker_id, result.job_id, {"status": completion.status})
        return {"job_id": completion.job_id, "lease_id": completion.lease_id, "status": completion.status}

    def recover(self, now: float) -> list[str]:
        expired = self.leases.expire(now)
        job_ids: list[str] = []
        for lease in expired:
            job_ids.append(lease.job_id)
            self.audit.record("job_requeued", lease.worker_id, lease.job_id, {"lease_id": lease.lease_id})
        return job_ids


def create_worker_app(service: WorkerService):
    if FastAPI is None:
        raise RuntimeError("FastAPI is required for the BOB worker HTTP service")
    app = FastAPI(title="PROJECT-BOB Worker Service")

    def require_auth(authorization: str | None) -> None:
        try:
            _auth_identity(authorization, service.auth_token)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @app.post("/workers/register")
    def register(payload: dict[str, Any], authorization: str | None = Header(default=None)):
        require_auth(authorization)
        try:
            registration = WorkerRegistration(str(payload.get("worker_id", "")), payload.get("platform"), frozenset(payload.get("capabilities", [])), dict(payload.get("resources", {})))
            return service.register(registration, float(payload.get("now", 0.0)))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/workers/heartbeat")
    def heartbeat(payload: dict[str, Any], authorization: str | None = Header(default=None)):
        require_auth(authorization)
        worker_id = str(payload.get("worker_id", ""))
        try:
            return service.heartbeat(worker_id, worker_id, float(payload.get("now", 0.0)), dict(payload.get("resources", {})))
        except (KeyError, PermissionError) as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.post("/jobs/claim")
    def claim(payload: dict[str, Any], authorization: str | None = Header(default=None)):
        require_auth(authorization)
        try:
            return service.claim(str(payload.get("job_id", "")), str(payload.get("worker_id", "")), str(payload.get("capability", "")), float(payload.get("now", 0.0)))
        except (KeyError, PermissionError, ValueError) as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.post("/jobs/result")
    def result(payload: dict[str, Any], authorization: str | None = Header(default=None)):
        require_auth(authorization)
        try:
            value = JobResult(str(payload.get("job_id", "")), str(payload.get("lease_id", "")), payload.get("status"), dict(payload.get("output", {})))
            return service.result(str(payload.get("worker_id", "")), value, float(payload.get("now", 0.0)))
        except (KeyError, PermissionError, ValueError) as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.get("/workers")
    def workers(authorization: str | None = Header(default=None)):
        require_auth(authorization)
        return [{"worker_id": w.worker_id, "platform": w.platform, "status": w.status, "capabilities": sorted(w.capabilities), "last_seen": w.last_seen} for w in service.registry.all()]

    return app
