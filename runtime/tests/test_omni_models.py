import pytest

from runtime.omni.models import ProviderConfig, ProviderKind


def test_provider_config_defaults_are_local_first():
    config = ProviderConfig(
        name="ollama",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="http://127.0.0.1:11434/v1",
    )
    assert config.enabled is True
    assert config.timeout_seconds == 15
    assert config.max_input_chars == 12000


def test_provider_config_rejects_non_http_urls():
    with pytest.raises(ValueError):
        ProviderConfig(
            name="bad",
            kind=ProviderKind.OPENAI_COMPATIBLE,
            base_url="file:///tmp/model",
        )
