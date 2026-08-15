from runtime.omni.catalog import configured_provider, default_catalog
from runtime.omni.models import ProviderKind, ProviderStatus


def test_catalog_contains_the_six_integrations():
    names = {profile.name for profile in default_catalog()}
    assert names == {
        "ollama-local-ai",
        "hermes-agent",
        "codex-mobile",
        "pocketpal",
        "offlinegpt",
        "hermes-relay",
    }


def test_supported_profiles_are_openai_compatible():
    supported = [p for p in default_catalog() if p.status is ProviderStatus.SUPPORTED]
    assert {p.name for p in supported} == {"ollama-local-ai", "hermes-agent"}
    assert all(p.kind is ProviderKind.OPENAI_COMPATIBLE for p in supported)


def test_unverified_profiles_cannot_become_active_implicitly():
    pocketpal = next(p for p in default_catalog() if p.name == "pocketpal")
    assert configured_provider(pocketpal, enabled=True) is None


def test_hermes_profile_can_be_explicitly_configured():
    hermes = next(p for p in default_catalog() if p.name == "hermes-agent")
    config = configured_provider(hermes, base_url="http://192.168.1.10:8642/v1", enabled=True)
    assert config is not None
    assert config.base_url.endswith("/v1")
