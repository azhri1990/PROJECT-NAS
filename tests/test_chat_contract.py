import importlib.util
import sys
from types import SimpleNamespace


def load_module():
    spec = importlib.util.spec_from_file_location("memory_injector_chat_test", "runtime/memory_injector.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_chat_accepts_prompt_and_returns_model_response(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_NAS_MEMORY_DB", str(tmp_path / "memory"))
    module = load_module()
    monkeypatch.setattr(module, "retrieve_context", lambda prompt: "\nMEMORY: prior context\n")

    class FakeCollection:
        def __init__(self):
            self.saved = []

        def add(self, **kwargs):
            self.saved.append(kwargs)

    collection = FakeCollection()
    monkeypatch.setattr(module, "collection", collection)

    def fake_post(url, json, timeout):
        assert json["model"] == module.MODEL_NAME
        assert "MEMORY: prior context" in json["prompt"]
        assert "hello" in json["prompt"]
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"response": "hello back"},
        )

    monkeypatch.setattr(module.requests, "post", fake_post)

    response = module.app.test_client().post("/chat", json={"prompt": "hello"})
    assert response.status_code == 200
    assert response.get_json() == {"response": "hello back"}
    assert len(collection.saved) == 1


def test_chat_rejects_missing_prompt(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_NAS_MEMORY_DB", str(tmp_path / "memory"))
    module = load_module()

    response = module.app.test_client().post("/chat", json={})
    assert response.status_code == 400
    assert "Missing 'prompt' field." in response.get_json()["error"]


def test_chat_maps_llm_transport_failure_to_502(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_NAS_MEMORY_DB", str(tmp_path / "memory"))
    module = load_module()
    monkeypatch.setattr(module, "retrieve_context", lambda prompt: "")

    def fake_post(*args, **kwargs):
        raise module.requests.exceptions.ConnectionError("offline")

    monkeypatch.setattr(module.requests, "post", fake_post)

    response = module.app.test_client().post("/chat", json={"prompt": "hello"})
    assert response.status_code == 502
    assert "Local LLM request failed" in response.get_json()["error"]
