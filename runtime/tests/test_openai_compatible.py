import requests
import pytest

from runtime.omni.models import ProviderConfig, ProviderKind
from runtime.omni.openai_compatible import OpenAICompatibleProvider, ProviderError


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, post_response=None, get_responses=None):
        self.post_response = post_response or FakeResponse(
            payload={"choices": [{"message": {"content": "ok"}}]}
        )
        self.get_responses = list(get_responses or [FakeResponse(payload={"status": "ok"})])
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.post_response

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.get_responses.pop(0)


def config():
    return ProviderConfig(
        name="ollama",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="http://127.0.0.1:11434/v1",
        model="qwen3",
    )


def test_chat_normalizes_openai_response():
    provider = OpenAICompatibleProvider(config(), session=FakeSession())
    result = provider.chat([{"role": "user", "content": "hello"}])
    assert result.text == "ok"
    assert result.provider == "ollama"
    assert result.model == "qwen3"


def test_chat_rejects_oversized_input():
    provider = OpenAICompatibleProvider(
        ProviderConfig(
            name="ollama",
            kind=ProviderKind.OPENAI_COMPATIBLE,
            base_url="http://127.0.0.1:11434/v1",
            max_input_chars=4,
        ),
        session=FakeSession(),
    )
    with pytest.raises(ProviderError, match="input exceeds"):
        provider.chat([{"role": "user", "content": "hello"}])


def test_health_falls_back_to_models_endpoint():
    session = FakeSession(get_responses=[FakeResponse(404), FakeResponse(200, {"data": []})])
    provider = OpenAICompatibleProvider(config(), session=session)
    health = provider.health()
    assert health.reachable is True
    assert health.detail == "ok"
    assert [call[1] for call in session.calls] == [
        "http://127.0.0.1:11434/health",
        "http://127.0.0.1:11434/v1/models",
    ]


def test_health_handles_timeout_without_leaking_details():
    class TimeoutSession(FakeSession):
        def get(self, url, **kwargs):
            raise requests.Timeout("secret-token-should-not-leak")

    health = OpenAICompatibleProvider(config(), session=TimeoutSession()).health()
    assert health.reachable is False
    assert health.detail == "Timeout"
    assert "secret" not in health.detail
