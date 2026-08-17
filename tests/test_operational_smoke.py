import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from runtime.backend import app
from runtime.orchestrator import IntentRouter


def test_health_endpoint_reports_structured_status():
    with patch("runtime.backend.health_report", return_value={"status": "healthy", "components": {"ollama": {"ok": True}}}):
        response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_chat_endpoint_accepts_bounded_local_request():
    with patch("runtime.backend._call_chat_worker", return_value={"response": "local ok"}) as worker:
        response = TestClient(app).post("/chat", json={"prompt": "hello", "context": ""})
    assert response.status_code == 200
    assert response.json()["response"] == "local ok"
    worker.assert_called_once_with("hello", "")


def test_chat_endpoint_rejects_oversized_prompt():
    response = TestClient(app).post("/chat", json={"prompt": "x" * 12001})
    assert response.status_code == 413


def test_orchestrator_produces_bounded_local_response():
    class FakeGateway:
        def execute(self, tool_name, payload):
            if tool_name == "prompt.get":
                return {"content": "SYSTEM"}
            if tool_name == "memory.read":
                return {"memories": [{"document": "MEMORY"}]}
            raise AssertionError(tool_name)

    class FakeRouter:
        def generate_with_fallback(self, context, **kwargs):
            assert len(context) <= 100
            assert "hello" in context
            return {"response": "ok"}, type("Route", (), {"selected": "local", "fallback": False})()

    result, route, truncated = IntentRouter(gateway=FakeGateway(), model_router=FakeRouter()).generate_response("hello", max_chars=100)
    assert result["response"] == "ok"
    assert route.selected == "local"
    assert truncated is False


def test_runtime_controller_exposes_required_commands():
    script = Path("runtime/project-nas.sh").read_text(encoding="utf-8")
    for command in ("start", "stop", "restart", "status", "doctor", "chat"):
        assert command in script
