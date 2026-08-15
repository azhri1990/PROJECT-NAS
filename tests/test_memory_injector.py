import importlib.util
import sys


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
