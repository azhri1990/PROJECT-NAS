from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from runtime.bob_command import BobCommandService

api = importlib.import_module("runtime.bob_command_api")


def test_service_rejects_policy_denied_capability() -> None:
    service = BobCommandService()
    with pytest.raises(PermissionError, match="denied by default"):
        service.submit(task="run arbitrary process", capability="execute_process")


def test_service_submits_and_routes_to_worker() -> None:
    service = BobCommandService()
    service.heartbeat(device_id="android-1", platform="android", capabilities=["read_repository"])
    job = service.submit(task="inspect repository status", capability="read_repository")
    assert job["state"] == "dispatched"
    assert job["worker_id"] == "android-1"


def test_service_blocks_when_no_worker_exists() -> None:
    service = BobCommandService()
    job = service.submit(task="inspect repository status", capability="read_repository")
    assert job["state"] == "blocked"
    assert "no online worker" in job["reason"]


def test_service_cancels_queued_job() -> None:
    service = BobCommandService()
    service.heartbeat(device_id="android-1", platform="android", capabilities=["read_repository"])
    job = service.submit(task="inspect repository status", capability="read_repository")
    service.queue.update(job["job_id"], state=importlib.import_module("07-AUTOMATION.bob.job_queue").JobState.QUEUED)
    cancelled = service.cancel(job["job_id"])
    assert cancelled["state"] == "cancelled"


def test_api_health_does_not_require_auth() -> None:
    client = TestClient(api.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "project-bob-command"


def test_api_fails_closed_without_server_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROJECT_BOB_AUTH_TOKEN", raising=False)
    client = TestClient(api.app)
    response = client.get("/workers")
    assert response.status_code == 503


def test_api_rejects_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROJECT_BOB_AUTH_TOKEN", "correct-token")
    client = TestClient(api.app)
    response = client.get("/workers", headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 401


def test_api_accepts_valid_token_and_heartbeat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROJECT_BOB_AUTH_TOKEN", "correct-token")
    api.service = BobCommandService()
    client = TestClient(api.app)
    response = client.post(
        "/workers/heartbeat",
        headers={"Authorization": "Bearer correct-token"},
        json={"device_id": "android-1", "platform": "android", "capabilities": ["read_repository"]},
    )
    assert response.status_code == 200
    assert response.json()["device_id"] == "android-1"


def test_api_denies_process_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROJECT_BOB_AUTH_TOKEN", "correct-token")
    api.service = BobCommandService()
    client = TestClient(api.app)
    response = client.post(
        "/jobs",
        headers={"Authorization": "Bearer correct-token"},
        json={"task": "run command", "capability": "execute_process"},
    )
    assert response.status_code == 403
