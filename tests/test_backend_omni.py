import importlib.util
import sys


BACKEND_PATH = "runtime/backend.py"


def load_backend():
    spec = importlib.util.spec_from_file_location("project_nas_backend_omni", BACKEND_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeService:
    def __init__(self, health=None):
        self._health = health

    def providers(self):
        return [
            {
                "name": "hermes-agent",
                "display_name": "Hermes Agent",
                "kind": "openai_compatible",
                "status": "supported",
                "configured": True,
                "description": "test",
                "base_url": "http://127.0.0.1:8642/v1",
                "model": "hermes-agent",
            }
        ]

    def health(self):
        return self._health if self._health is not None else [
            {
                "name": "hermes-agent",
                "reachable": True,
                "authenticated": True,
                "latency_ms": 2.0,
                "detail": "ok",
            }
        ]


def test_omni_provider_endpoint_does_not_expose_secrets(monkeypatch):
    backend = load_backend()
    monkeypatch.setattr(backend, "get_omni_service", lambda: FakeService())

    payload = backend.omni_providers()
    assert payload["providers"][0]["name"] == "hermes-agent"
    assert "api_key" not in payload["providers"][0]


def test_omni_health_reports_healthy_when_all_enabled_providers_are_reachable(monkeypatch):
    backend = load_backend()
    monkeypatch.setattr(backend, "get_omni_service", lambda: FakeService())

    payload = backend.omni_health()
    assert payload["status"] == "ok"
    assert payload["providers"][0]["reachable"] is True


def test_omni_health_reports_unconfigured_without_providers(monkeypatch):
    backend = load_backend()
    monkeypatch.setattr(backend, "get_omni_service", lambda: FakeService(health=[]))

    payload = backend.omni_health()
    assert payload["status"] == "unconfigured"
