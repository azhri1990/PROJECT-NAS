import importlib.util
import sys
from types import SimpleNamespace


def load_module():
    spec = importlib.util.spec_from_file_location("memory_injector", "runtime/memory_injector.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_model_defaults_to_documented_local_model(monkeypatch):
    monkeypatch.delenv("PROJECT_NAS_OLLAMA_MODEL", raising=False)
    module = load_module()
    assert module.MODEL_NAME == "llama3.2:3b"


def test_model_can_be_overridden_by_environment(monkeypatch):
    monkeypatch.setenv("PROJECT_NAS_OLLAMA_MODEL", "custom-model")
    module = load_module()
    assert module.MODEL_NAME == "custom-model"


def test_ollama_url_is_configurable(monkeypatch):
    monkeypatch.setenv("PROJECT_NAS_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    module = load_module()
    assert module.OLLAMA_URL == "http://127.0.0.1:11434/api/generate"

def test_chat_rejects_oversized_prompt(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_NAS_MEMORY_DB", str(tmp_path / "memory"))
    monkeypatch.setenv("PROJECT_NAS_MAX_PROMPT_CHARS", "10")
    module = load_module()

    response = module.app.test_client().post(
        "/chat",
        json={"prompt": "x" * 11},
    )

    assert response.status_code == 413
    assert "prompt" in response.get_json()["error"].lower()


def test_chat_rejects_oversized_context(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_NAS_MEMORY_DB", str(tmp_path / "memory"))
    monkeypatch.setenv("PROJECT_NAS_MAX_CONTEXT_CHARS", "10")
    module = load_module()

    response = module.app.test_client().post(
        "/chat",
        json={
            "prompt": "hello",
            "context": "x" * 11,
        },
    )

    assert response.status_code == 413
    assert "context" in response.get_json()["error"].lower()


def test_chat_rejects_non_loopback_ollama_url(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_NAS_MEMORY_DB", str(tmp_path / "memory"))
    monkeypatch.setenv(
        "PROJECT_NAS_OLLAMA_URL",
        "http://192.168.1.50:11434/api/generate",
    )
    module = load_module()

    response = module.app.test_client().post(
        "/chat",
        json={"prompt": "hello"},
    )

    assert response.status_code == 503
    assert "local" in response.get_json()["error"].lower()


def test_chat_truncates_oversized_model_response(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_NAS_MEMORY_DB", str(tmp_path / "memory"))
    monkeypatch.setenv("PROJECT_NAS_MAX_RESPONSE_CHARS", "20")
    module = load_module()

    monkeypatch.setattr(module, "retrieve_context", lambda prompt: "")

    class FakeCollection:
        def __init__(self):
            self.saved = []

        def add(self, **kwargs):
            self.saved.append(kwargs)

    collection = FakeCollection()
    monkeypatch.setattr(module, "collection", collection)

    def fake_post(*args, **kwargs):
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"response": "A" * 100},
        )

    monkeypatch.setattr(module.requests, "post", fake_post)

    response = module.app.test_client().post(
        "/chat",
        json={"prompt": "hello"},
    )

    assert response.status_code == 200
    assert len(response.get_json()["response"]) == 20
    assert len(collection.saved) == 1
    saved = collection.saved[0]["documents"][0]
    assert len(saved) <= 20 + len("User asked: hello\nAI replied: ")
