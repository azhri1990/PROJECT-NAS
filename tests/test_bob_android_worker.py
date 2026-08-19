from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.bob.android_state import AndroidState
from runtime.bob.android_worker import AndroidWorker, AndroidWorkerConfig


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def make_worker(tmp_path: Path, responses=None):
    calls = []
    responses = iter(responses or [{"status": "ok"}])

    def opener(request, timeout):
        calls.append(request)
        return FakeResponse(next(responses))

    config = AndroidWorkerConfig("android-01", "http://127.0.0.1:8787", "secret", frozenset({"read_repository"}))
    return AndroidWorker(config, AndroidState(tmp_path / "state.json"), opener), calls


def test_config_rejects_empty_token(tmp_path):
    with pytest.raises(ValueError):
        AndroidWorkerConfig("android-01", "http://127.0.0.1:8787", "")


def test_register_and_heartbeat(tmp_path):
    worker, calls = make_worker(tmp_path, [{"worker_id": "android-01"}, {"status": "available"}])
    assert worker.register(now=10)["worker_id"] == "android-01"
    assert worker.heartbeat(now=11)["status"] == "available"
    assert len(calls) == 2
    assert calls[0].get_header("Authorization") == "Bearer secret"


def test_claim_requires_declared_capability(tmp_path):
    worker, _ = make_worker(tmp_path)
    worker.register(now=1)
    with pytest.raises(PermissionError):
        worker.claim("job-1", "execute_process", now=2)


def test_result_is_queued_until_server_ack(tmp_path):
    worker, _ = make_worker(tmp_path, [{"worker_id": "android-01"}, {"status": "succeeded"}])
    worker.register(now=1)
    result = worker.report_result("job-1", "lease-1", "succeeded", {"ok": True}, now=2)
    assert result["status"] == "succeeded"
    assert worker.state.load()["pending_results"] == {}


def test_result_survives_network_failure(tmp_path):
    worker, _ = make_worker(tmp_path, [{"worker_id": "android-01"}])
    worker.register(now=1)

    def offline(*_args, **_kwargs):
        raise OSError("offline")

    worker._opener = offline
    with pytest.raises(OSError):
        worker.report_result("job-1", "lease-1", "failed", {"reason": "offline"}, now=2)
    assert "lease-1" in worker.state.load()["pending_results"]
