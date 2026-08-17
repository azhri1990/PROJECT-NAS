from importlib.util import module_from_spec, spec_from_file_location
import sys


def load_module():
    spec = spec_from_file_location("memory_injector_model_routing", "runtime/memory_injector.py")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_resolve_local_model_prefers_configured_without_network(monkeypatch):
    module = load_module()
    called = []
    monkeypatch.setattr(module, "discover_local_models", lambda base_url=None: called.append(base_url) or ["custom-model", "llama3.2:3b"])

    assert module.resolve_local_model("custom-model") == "custom-model"
    assert called == [None]


def test_resolve_local_model_uses_known_fallback_before_chat(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "discover_local_models", lambda base_url=None: ["llama3.2:3b", "z-model"])

    assert module.resolve_local_model("missing-model") == "llama3.2:3b"


def test_resolve_local_model_keeps_configured_when_discovery_is_unavailable(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "discover_local_models", lambda base_url=None: [])

    assert module.resolve_local_model("configured-model") == "configured-model"


def test_resolve_local_model_caches_discovery_for_short_period(monkeypatch):
    module = load_module()
    calls = []
    monkeypatch.setattr(module, "discover_local_models", lambda base_url=None: calls.append(base_url) or ["llama3.2:3b"])

    assert module.resolve_local_model("missing-model") == "llama3.2:3b"
    assert module.resolve_local_model("missing-model") == "llama3.2:3b"
    assert calls == [None]
