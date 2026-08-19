"""Authenticated HTTP worker service for PROJECT-BOB.

This module exposes worker lifecycle and lease operations only. It deliberately
contains no arbitrary shell or command-execution endpoint.
"""
from __future__ import annotations

import os
from typing import Any

from .audit import WorkerAudit
from .job_lease import JobLeaseStore
from .worker_protocol import JobResult, WorkerRegistration
from .worker_registry import WorkerRegistry

try:
    from fastapi import FastAPI, Header, HTTPException
except ImportError:  # pragma: no cover - runtime dependency is part of PROJECT-NAS
    FastAPI = None  # type: ignore[assignment]


def _auth_identity(authorization: str | None, expected: str | None) -> str:
    if not expected:
        raise HTTPException(status_code=503, detail="worker authentication is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="authentication required")
    token = authorization[7:].strip()
    if token != expected:
        raise HTTPException(status_code=401, detail="invalid authentication token")
    return "authenticated-worker"


class WorkerService:
    def __init__(self, registry: WorkerRegistry, leases: JobLeaseStore, audit: WorkerAudit | None = None, auth_token: str | None = None) -> None:
        self.registry = registry
        self.leases = leases
        self.audit = audit or WorkerAudit()
        self.auth_token = auth_token if auth_token is not None else os.getenv("PROJECT_BOB_AUTH_TOKEN")

    def register(self, registration: WorkerRegistration, now: float = 0.0) -> dict[str, Any]:
        record = self.registry.register_worker(registration, now=now)
        self.audit.record("worker_registered", record.worker_id, details={"platform": record.platform})
        return {"worker_id": record.worker_id, "status": record.status, "platform": record.platform, "capabilities": sorted(record.capabilities)}

    def heartbeat(self, worker_id: str, identity: str, now: float, resources: dict[str, float] | None = None) -> dict[str, Any]:
        record = self.registry.heartbeat(worker_id, identity, now, resources)
        self.audit.record("worker_heartbeat", worker_id)
        return {"worker_id": record.worker_id, "status": record.status, "last_seen": record.last_seen}

    def claim(self, job_id: str, worker_id: str, capability: str, now: float, policy_allowed: bool) -> dict[str, Any]:
        worker = self.registry.get(worker_id)
        if worker is None or worker.status != "available":
            raise PermissionError("worker is not registered and available")
        if not worker.supports(capability):
            raise PermissionError("worker does not advertise required capability")
        if not policy_allowed:
            self.audit.record("job_denied", worker_id, job_id, {"reason": "policy denied"})
            raise PermissionError("NAS policy denied worker job claim")
        lease = self.leases.claim(job_id, worker_id, now)
        self.audit.record("job_claimed", worker_id, job_id, {"lease_id": lease.lease_id})
        return {"job_id": lease.job_id, "lease_id": lease.lease_id, "expires_at": lease.expires_at}

    def result(self, worker_id: str, result: JobResult, now: float) -> dict[str, Any]:
        completion = self.leases.complete(result.lease_id, worker_id, result, now)
        self.audit.record("job_completed", worker_id, result.job_id, {"status": completion.status})
        return {"job_id": completion.job_id, "lease_id": completion.lease_id, "status": completion.status}


def create_worker_app(service: WorkerService):
    if FastAPI is None:
        raise RuntimeError("FastAPI is required for the BOB worker HTTP service")
    app = FastAPI(title="PROJECT-BOB Worker Service")

    def require_auth(authorization: str | None) -> None:
        _auth_identity(authorization, service.auth_token)

    @app.post("/workers/register")
    def register(payload: dict[str, Any], authorization: str | None = Header(default=None)):
        require_auth(authorization)
        registration = WorkerRegistration(
            worker_id=str(payload.get("worker_id", "")),
            platform=payload.get("platform"),
            capabilities=frozenset(payload.get("capabilities", [])),
            resources=dict(payload.get("resources", {})),
        )
        return service.register(registration, float(payload.get("now", 0.0)))

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
            return service.claim(
                str(payload.get("job_id", "")),
                str(payload.get("worker_id", "")),
                str(payload.get("capability", "")),
                float(payload.get("now", 0.0)),
                bool(payload.get("policy_allowed", False)),
            )
        except (KeyError, PermissionError, ValueError) as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.post("/jobs/result")
    def result(payload: dict[str, Any], authorization: str | None = Header(default=None)):
        require_auth(authorization)
        try:
            value = JobResult(
                job_id=str(payload.get("job_id", "")),
                lease_id=str(payload.get("lease_id", "")),
                status=payload.get("status"),
                output=dict(payload.get("output", {})),
            )
            return service.result(str(payload.get("worker_id", "")), value, float(payload.get("now", 0.0)))
        except (KeyError, PermissionError, ValueError) as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.get("/workers")
    def workers(authorization: str | None = Header(default=None)):
        require_auth(authorization)
        return [
            {"worker_id": w.worker_id, "platform": w.platform, "status": w.status, "capabilities": sorted(w.capabilities), "last_seen": w.last_seen}
            for w in service.registry.all()
        ]

    return app
