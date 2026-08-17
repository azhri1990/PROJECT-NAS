from fastapi.testclient import TestClient

import runtime.backend as backend


def test_health_endpoint_returns_aggregate_without_memory_contents(monkeypatch):
    for name in ("ollama", "memory_api", "memory_sqlite", "repository", "model"):
        monkeypatch.setattr(backend, f"_probe_{name}", lambda: {"ok": True})
    payload = TestClient(backend.app).get("/health").json()
    assert payload["status"] == "healthy"
    assert "memories" not in payload
    assert "document" not in str(payload)


def test_prompt_endpoint_is_bounded(monkeypatch):
    monkeypatch.setattr(backend, "PROMPT_PATHS", [__file__])
    response = TestClient(backend.app).get("/prompt")
    assert response.status_code == 200
    payload = response.json()
    assert payload["chars"] == len(payload["content"])
    assert payload["chars"] <= 12000


def test_control_plane_unknown_namespace_is_denied():
    response = TestClient(backend.app).post("/tools/shell.run", json={"command": "id"})
    assert response.status_code == 403
