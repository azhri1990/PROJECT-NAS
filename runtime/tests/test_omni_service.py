from runtime.omni.models import ChatResult, ProviderConfig, ProviderKind, ProviderHealth
from runtime.omni.policy import PolicyEngine
from runtime.omni.providers import AIProvider, ProviderRegistry
from runtime.omni.service import OmniService


class FakeProvider(AIProvider):
    def health(self):
        return ProviderHealth(self.config.name, True, None, 1.0, "ok")

    def chat(self, messages):
        return ChatResult("ok", self.config.name, self.config.model, 1.0)


def test_chat_passes_through_policy_and_provider():
    config = ProviderConfig(
        name="test",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="http://127.0.0.1:1234/v1",
        model="test-model",
    )
    registry = ProviderRegistry()
    registry.register(config, FakeProvider(config))
    service = OmniService(registry, profiles=(), policy=PolicyEngine())

    result = service.chat("test", [{"role": "user", "content": "hello"}])
    assert result.text == "ok"
    assert result.provider == "test"
