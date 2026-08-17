import importlib.util
import sys
from types import SimpleNamespace


def load_module():
    spec = importlib.util.spec_from_file_location("memory_injector_e2e_test", "runtime/memory_injector.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_chat_end_to_end_with_ollama_compatible_http(monkeypatch, tmp_path):
    """Exercise the complete /chat request path without requiring Ollama in CI."""
    monkeypatch.setenv("PROJECT_NAS_MEMORY_DB", str(tmp_path / "memory"))
    monkeypatch.setenv("PROJECT_NAS_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    module = load_module()

    class FakeCollection:
        def __init__(self):
            self.saved = []

        def query(self, **kwargs):
            return {"documents": [["prior memory"]]}

        def add(self, **kwargs):
            self.saved.append(kwargs)

    collection = FakeCollection()
    monkeypatch.setattr(module, "collection", collection)

    def fake_post(url, json, timeout):
        assert url == module.OLLAMA_URL
        assert json["model"] == module.MODEL_NAME
        assert json["stream"] is False
        assert "prior memory" in json["prompt"]
        assert "hello" in json["prompt"]
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"response": "hello from local model"},
        )

    monkeypatch.setattr(module.requests, "post", fake_post)

    response = module.app.test_client().post("/chat", json={"prompt": "hello"})

    assert response.status_code == 200
    assert response.get_json() == {"response": "hello from local model"}
    assert collection.saved == []


def test_health_exposes_configured_local_ollama_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_NAS_MEMORY_DB", str(tmp_path / "memory"))
    monkeypatch.setenv("PROJECT_NAS_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    module = load_module()

    response = module.app.test_client().get("/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["ollama_url"] == "http://127.0.0.1:11434/api/generate"
    assert payload["model"] == module.MODEL_NAME
