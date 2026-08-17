import pytest
import requests

from runtime.local_model_router import LocalModelRouter


def test_loopback_urls_only():
    assert LocalModelRouter.is_loopback_url("http://127.0.0.1:11434")
    assert LocalModelRouter.is_loopback_url("http://localhost:11434")
    assert LocalModelRouter.is_loopback_url("http://[::1]:11434")
    assert not LocalModelRouter.is_loopback_url("https://example.com")
    assert not LocalModelRouter.is_loopback_url("http://192.168.1.10:11434")


def test_route_prefers_configured_then_known_local_fallbacks():
    router = LocalModelRouter("custom:7b")
    route = router.route(["llama3.2:1b", "llama3.1:8b"])
    assert route.selected == "llama3.2:1b"
    assert route.fallback is True


def test_route_uses_configured_model_when_available():
    router = LocalModelRouter("llama3.2:3b")
    route = router.route(["llama3.2:3b", "llama3.2:1b"])
    assert route.selected == "llama3.2:3b"
    assert route.fallback is False


def test_discover_rejects_non_loopback(monkeypatch):
    router = LocalModelRouter("llama3.2:3b", base_url="https://example.com")
    called = []
    monkeypatch.setattr("runtime.local_model_router.requests.get", lambda *args, **kwargs: called.append(args))
    assert router.discover() == ()
    assert called == []


def test_route_empty_when_no_models():
    router = LocalModelRouter("llama3.2:3b")
    route = router.route([])
    assert route.selected is None
    assert route.fallback is False


def test_generate_rejects_remote_endpoint():
    router = LocalModelRouter("llama3.2:3b", base_url="https://example.com")
    with pytest.raises(ValueError, match="loopback"):
        router.generate("hello")


def test_generate_validates_prediction_budget():
    router = LocalModelRouter("llama3.2:3b")
    with pytest.raises(ValueError, match="num_predict"):
        router.generate("hello", num_predict=0)
    with pytest.raises(ValueError, match="num_predict"):
        router.generate("hello", num_predict=4097)


def test_fallback_on_connection_failure(monkeypatch):
    router = LocalModelRouter("missing:model")
    calls = []

    def fake_post(url, **kwargs):
        calls.append(kwargs["json"]["model"])
        if len(calls) == 1:
            raise requests.ConnectionError("ollama unavailable")
        return type("Response", (), {"raise_for_status": lambda self: None, "json": lambda self: {"response": "fallback ok"}})()

    monkeypatch.setattr("runtime.local_model_router.requests.post", fake_post)
    monkeypatch.setattr(router, "discover_route", lambda: router.route(["llama3.2:1b"]))
    result, route = router.generate_with_fallback("hello")
    assert result["response"] == "fallback ok"
    assert route.selected == "llama3.2:1b"
    assert route.fallback is True
    assert calls == ["missing:model", "llama3.2:1b"]


def test_fallback_on_timeout(monkeypatch):
    router = LocalModelRouter("missing:model")
    calls = []

    def fake_post(url, **kwargs):
        calls.append(kwargs["json"]["model"])
        if len(calls) == 1:
            raise requests.Timeout("ollama timed out")
        return type("Response", (), {"raise_for_status": lambda self: None, "json": lambda self: {"response": "fallback ok"}})()

    monkeypatch.setattr("runtime.local_model_router.requests.post", fake_post)
    monkeypatch.setattr(router, "discover_route", lambda: router.route(["llama3.2:1b"]))
    result, route = router.generate_with_fallback("hello")
    assert result["response"] == "fallback ok"
    assert route.selected == "llama3.2:1b"
    assert calls == ["missing:model", "llama3.2:1b"]


def test_unexpected_server_error_is_not_hidden(monkeypatch):
    router = LocalModelRouter("llama3.2:3b")
    response = type("Response", (), {"status_code": 500})()
    monkeypatch.setattr("runtime.local_model_router.requests.post", lambda *args, **kwargs: (_ for _ in ()).throw(requests.HTTPError(response=response)))
    with pytest.raises(requests.HTTPError):
        router.generate_with_fallback("hello")
