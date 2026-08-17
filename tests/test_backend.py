import importlib.util
import json
import sys

from fastapi.testclient import TestClient

import runtime.backend as backend_module

BACKEND_PATH = "runtime/backend.py"


def load_backend():
    spec = importlib.util.spec_from_file_location("project_nas_backend", BACKEND_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_session_db_is_configurable(tmp_path, monkeypatch):
    db_path = tmp_path / "session.db"
    monkeypatch.setenv("PROJECT_NAS_SESSION_DB", str(db_path))
    backend = load_backend()
    assert backend.resolve_session_db() == str(db_path)


def test_tool_endpoint_denies_repo_progress(monkeypatch):
    backend = load_backend()
    monkeypatch.setattr(backend, "run_git_info", lambda commits: {"branch": "test", "status_porcelain": "", "recent_commits": ["one"][:commits]})
    backend.TOOL_GATEWAY = backend.build_default_gateway(backend.run_git_info)
    client = TestClient(backend.app)
    response = client.post("/tools/repo.progress", json={"commits": 1})
    assert response.status_code == 403


def test_tool_endpoint_rejects_unknown_or_process_tool():
    backend = load_backend()
    client = TestClient(backend.app)
    assert client.post("/tools/missing", json={}).status_code == 403
    assert client.post("/tools/shell.run", json={"command": "whoami"}).status_code == 403


def test_progress_endpoint_uses_tool_gateway(monkeypatch):
    backend = load_backend()
    called = []
    def fake_execute(name, payload):
        called.append((name, payload))
        return {"branch": "test"}
    monkeypatch.setattr(backend.TOOL_GATEWAY, "execute", fake_execute)
    response = TestClient(backend.app).get("/progress?commits=3")
    assert response.status_code == 200
    assert response.json() == {"branch": "test"}
    assert called == [("status.progress", {"commits": 3})]


def test_custom_plugin_execution_is_disabled(tmp_path):
    backend = load_backend()
    backend.PLUGIN_DIR = str(tmp_path)
    (tmp_path / "test_plugin.py").write_text("def handle(payload):\n    return {'executed': True}\n", encoding="utf-8")
    response = TestClient(backend.app).post("/custom/test_plugin", json={})
    assert response.status_code in (404, 405, 410)


def test_prompt_reader_prefers_canonical_and_reports_truncation(tmp_path, monkeypatch):
    canonical = tmp_path / "MASTER_PROMPT.md"
    fallback = tmp_path / "SUMMARY.md"
    canonical.write_text("abcdefghij", encoding="utf-8")
    fallback.write_text("fallback", encoding="utf-8")
    monkeypatch.setattr(backend_module, "PROMPT_PATHS", [str(canonical), str(fallback)])
    result = backend_module.read_prompt(5)
    assert result["path"] == str(canonical)
    assert result["content"] == "abcde"
    assert result["chars"] == 5
    assert result["truncated"] is True


def test_prompt_reader_falls_back_when_canonical_missing(tmp_path, monkeypatch):
    fallback = tmp_path / "SUMMARY.md"
    fallback.write_text("fallback", encoding="utf-8")
    monkeypatch.setattr(backend_module, "PROMPT_PATHS", [str(tmp_path / "missing"), str(fallback)])
    result = backend_module.read_prompt()
    assert result["path"] == str(fallback)
    assert result["content"] == "fallback"
    assert result["truncated"] is False


def test_prompt_reader_missing_prompt_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(backend_module, "PROMPT_PATHS", [str(tmp_path / "missing")])
    assert backend_module.read_prompt() == {"path": None, "content": "", "chars": 0, "truncated": False}


def test_health_state_aggregation(monkeypatch):
    passing = {"ok": True}
    degraded = {"ok": False, "error": "optional failure"}
    for name in ("ollama", "memory_api", "memory_sqlite", "repository", "model"):
        monkeypatch.setattr(backend_module, f"_probe_{name}", lambda value=passing: value)
    assert backend_module.health_report()["status"] == "healthy"
    monkeypatch.setattr(backend_module, "_probe_memory_sqlite", lambda: degraded)
    report = backend_module.health_report()
    assert report["status"] == "degraded"
    assert report["components"]["memory_sqlite"]["error"] == "optional failure"
    monkeypatch.setattr(backend_module, "_probe_ollama", lambda: degraded)
    assert backend_module.health_report()["status"] == "unavailable"


def test_health_contains_no_memory_contents(monkeypatch):
    for name in ("ollama", "memory_api", "memory_sqlite", "repository", "model"):
        monkeypatch.setattr(backend_module, f"_probe_{name}", lambda: {"ok": True})
    payload = backend_module.health_report()
    assert "memories" not in payload
    assert "document" not in json.dumps(payload)


def test_control_plane_http_tools(monkeypatch):
    backend = load_backend()
    for name in ("ollama", "memory_api", "memory_sqlite", "repository", "model"):
        monkeypatch.setattr(backend, f"_probe_{name}", lambda: {"ok": True})
    client = TestClient(backend.app)
    for tool, payload in (
        ("status.health", {}),
        ("status.progress", {"commits": 1}),
        ("prompt.get", {}),
        ("memory.read", {"limit": 1}),
    ):
        response = client.post(f"/tools/{tool}", json=payload)
        assert response.status_code == 200, (tool, response.text)
        assert isinstance(response.json(), dict)


def test_http_error_mapping(monkeypatch):
    backend = load_backend()
    class FakeGateway:
        def execute(self, name, payload):
            if name == "missing.tool":
                raise KeyError(name)
            if name == "blocked.tool":
                raise PermissionError("blocked")
            if name == "bad.tool":
                raise ValueError("bad payload")
            if name == "slow.tool":
                raise TimeoutError("timed out")
            return {"ok": True}
    monkeypatch.setattr(backend, "TOOL_GATEWAY", FakeGateway())
    client = TestClient(backend.app)
    assert client.post("/tools/missing.tool", json={}).status_code == 404
    assert client.post("/tools/blocked.tool", json={}).status_code == 403
    assert client.post("/tools/bad.tool", json={}).status_code == 400
    assert client.post("/tools/slow.tool", json={}).status_code == 504


def test_todo_create_rejects_unsupported_fields_and_invalid_status():
    backend = load_backend()
    client = TestClient(backend.app)
    assert client.post("/todos", json={"id": "1", "title": "x", "extra": "nope"}).status_code == 400
    assert client.post("/todos", json={"id": "2", "title": "x", "status": "running"}).status_code == 400


def test_todo_create_bounds_text_fields(tmp_path, monkeypatch):
    db_path = tmp_path / "session.db"
    monkeypatch.setenv("PROJECT_NAS_SESSION_DB", str(db_path))
    backend = load_backend()
    client = TestClient(backend.app)
    response = client.post("/todos", json={"id": "1", "title": "x" * (backend.MAX_TODO_TITLE_CHARS + 1)})
    assert response.status_code == 413


def test_todo_update_requires_supported_nonempty_payload(tmp_path, monkeypatch):
    db_path = tmp_path / "session.db"
    monkeypatch.setenv("PROJECT_NAS_SESSION_DB", str(db_path))
    backend = load_backend()
    client = TestClient(backend.app)
    assert client.put("/todos/missing", json={}).status_code == 400
    assert client.put("/todos/missing", json={"extra": "nope"}).status_code == 400


def test_todo_lifecycle_accepts_only_governed_values(tmp_path, monkeypatch):
    db_path = tmp_path / "session.db"
    monkeypatch.setenv("PROJECT_NAS_SESSION_DB", str(db_path))
    backend = load_backend()
    client = TestClient(backend.app)
    created = client.post("/todos", json={"id": "todo-1", "title": "Ship runtime", "status": "pending"})
    assert created.status_code == 200
    updated = client.put("/todos/todo-1", json={"status": "completed"})
    assert updated.status_code == 200
    todos = client.get("/todos").json()["todos"]
    assert todos[0]["status"] == "completed"
