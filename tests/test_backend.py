import importlib.util
import sys

from fastapi.testclient import TestClient


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
    monkeypatch.setattr(
        backend,
        "run_git_info",
        lambda commits: {"branch": "test", "status_porcelain": "", "recent_commits": ["one"][:commits]},
    )
    backend.TOOL_GATEWAY = backend.build_default_gateway(backend.run_git_info)
    client = TestClient(backend.app)

    response = client.post("/tools/repo.progress", json={"commits": 1})

    assert response.status_code == 403


def test_tool_endpoint_rejects_unknown_or_process_tool():
    backend = load_backend()
    client = TestClient(backend.app)

    unknown = client.post("/tools/missing", json={})
    assert unknown.status_code == 403

    process = client.post("/tools/shell.run", json={"command": "whoami"})
    assert process.status_code == 403

def test_custom_plugin_execution_is_disabled(tmp_path):
    backend = load_backend()
    backend.PLUGIN_DIR = str(tmp_path)

    (tmp_path / "test_plugin.py").write_text(
        "def handle(payload):\n"
        "    return {'executed': True}\n",
        encoding="utf-8",
    )

    client = TestClient(backend.app)
    response = client.post("/custom/test_plugin", json={})

    assert response.status_code in (404, 405, 410)
