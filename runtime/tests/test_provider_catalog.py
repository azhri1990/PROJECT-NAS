from runtime.omni.catalog import configured_provider, default_catalog
from runtime.omni.models import ProviderKind, ProviderStatus


def test_catalog_contains_the_six_integrations():
    names = {profile.name for profile in default_catalog() if profile.name != "custom-openai-compatible"}
    assert names == {
        "ollama-local-ai",
        "hermes-agent",
        "codex-mobile",
        "pocketpal",
        "offlinegpt",
        "hermes-relay",
    }


def test_only_ollama_and_generic_endpoint_are_supported_adapters():
    supported = [p for p in default_catalog() if p.status is ProviderStatus.SUPPORTED]
    assert {p.name for p in supported} == {"ollama-local-ai", "custom-openai-compatible"}
    assert all(p.kind is ProviderKind.OPENAI_COMPATIBLE for p in supported)


def test_unverified_profiles_cannot_become_active_implicitly():
    pocketpal = next(p for p in default_catalog() if p.name == "pocketpal")
    hermes = next(p for p in default_catalog() if p.name == "hermes-agent")
    assert configured_provider(pocketpal, enabled=True) is None
    assert configured_provider(hermes, enabled=True) is None


def test_generic_endpoint_can_be_explicitly_configured():
    compatible = next(p for p in default_catalog() if p.name == "custom-openai-compatible")
    config = configured_provider(compatible, base_url="http://192.168.1.10:8642/v1", enabled=True)
    assert config is not None
    assert config.base_url.endswith("/v1")
