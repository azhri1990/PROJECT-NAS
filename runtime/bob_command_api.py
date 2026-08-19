"""Private, authenticated FastAPI surface for PROJECT-BOB commands."""

from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from runtime.bob_command import BobCommandService


class JobRequest(BaseModel):
    task: str = Field(min_length=1, max_length=4000)
    capability: str = Field(min_length=1, max_length=64)


class HeartbeatRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    platform: str = Field(min_length=1, max_length=64)
    capabilities: list[str] = Field(default_factory=list, max_length=32)
    online: bool = True
    cost: float = Field(default=0.0, ge=0.0, le=100000.0)


def _configured_token() -> str | None:
    token = os.environ.get("PROJECT_BOB_AUTH_TOKEN")
    return token if token else None


def require_auth(authorization: str | None = Header(default=None)) -> None:
    expected = _configured_token()
    if expected is None:
        raise HTTPException(status_code=503, detail="BOB authentication is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    supplied = authorization[7:]
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="invalid bearer token")


service = BobCommandService()
app = FastAPI(title="PROJECT-BOB Command API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "project-bob-command"}


@app.post("/jobs", dependencies=[Depends(require_auth)])
def submit_job(request: JobRequest) -> dict[str, Any]:
    try:
        return service.submit(task=request.task, capability=request.capability)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/jobs/{job_id}", dependencies=[Depends(require_auth)])
def get_job(job_id: str) -> dict[str, Any]:
    try:
        return service.status(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc


@app.post("/jobs/{job_id}/cancel", dependencies=[Depends(require_auth)])
def cancel_job(job_id: str) -> dict[str, Any]:
    try:
        return service.cancel(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/workers", dependencies=[Depends(require_auth)])
def get_workers() -> dict[str, Any]:
    return {"workers": service.workers()}


@app.post("/workers/heartbeat", dependencies=[Depends(require_auth)])
def worker_heartbeat(request: HeartbeatRequest) -> dict[str, Any]:
    try:
        return service.heartbeat(device_id=request.device_id, platform=request.platform, capabilities=request.capabilities, online=request.online, cost=request.cost)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
