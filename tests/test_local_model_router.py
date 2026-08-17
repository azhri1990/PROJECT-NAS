import pytest

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
