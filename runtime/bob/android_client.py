"""Minimal authenticated HTTP client for activating an Android BOB worker."""
from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .android_activation import WorkerConfig


@dataclass(frozen=True)
class ActivationResult:
    ok: bool
    status: int | None
    payload: dict
    error: str | None = None


def _post(config: WorkerConfig, path: str, payload: dict, timeout: float = 8.0) -> ActivationResult:
    request = Request(
        f"{config.endpoint.rstrip('/')}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.token}",
            "Content-Type": "application/json",
            "User-Agent": "PROJECT-BOB-Android-Worker/1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return ActivationResult(True, response.status, json.loads(body) if body else {})
    except HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
            payload = json.loads(body) if body else {}
        except (OSError, ValueError):
            payload = {}
        return ActivationResult(False, exc.code, payload, f"HTTP {exc.code}")
    except (URLError, TimeoutError, OSError) as exc:
        return ActivationResult(False, None, {}, str(exc))


def register(config: WorkerConfig) -> ActivationResult:
    return _post(config, "/workers/register", {
        "worker_id": config.worker_id,
        "platform": config.platform,
        "capabilities": list(config.capabilities),
        "resources": {},
    })


def heartbeat(config: WorkerConfig, now: float) -> ActivationResult:
    return _post(config, "/workers/heartbeat", {
        "worker_id": config.worker_id,
        "now": now,
        "resources": {},
    })


def status(config: WorkerConfig, timeout: float = 8.0) -> ActivationResult:
    request = Request(
        f"{config.endpoint.rstrip('/')}/workers",
        headers={"Authorization": f"Bearer {config.token}", "User-Agent": "PROJECT-BOB-Android-Worker/1"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            payload = json.loads(body) if body else {}
            return ActivationResult(True, response.status, {"workers": payload})
    except HTTPError as exc:
        return ActivationResult(False, exc.code, {}, f"HTTP {exc.code}")
    except (URLError, TimeoutError, OSError) as exc:
        return ActivationResult(False, None, {}, str(exc))
