from runtime.omni.security import (
    classify_provider_action,
    is_allowed_provider_url,
    redact_provider_metadata,
)


def test_loopback_is_allowed():
    assert is_allowed_provider_url("http://127.0.0.1:11434/v1") is True
    assert is_allowed_provider_url("http://localhost:8642/v1") is True


def test_lan_host_requires_explicit_allowlist():
    assert is_allowed_provider_url("http://192.168.1.20:8642/v1") is False
    assert is_allowed_provider_url("http://192.168.1.20:8642/v1", {"192.168.1.20"}) is True


def test_unsupported_and_credential_urls_are_rejected():
    assert is_allowed_provider_url("file:///tmp/model") is False
    assert is_allowed_provider_url("javascript:alert(1)") is False
    assert is_allowed_provider_url("http://user:pass@example.com") is False


def test_public_hosts_must_be_allowlisted():
    assert is_allowed_provider_url("https://example.com/v1") is False
    assert is_allowed_provider_url("https://example.com/v1", {"example.com"}) is True


def test_sensitive_metadata_is_redacted():
    safe = redact_provider_metadata(
        {"name": "hermes-agent", "api_key_env": "HERMES_KEY", "authorization": "Bearer secret"}
    )
    assert safe["name"] == "hermes-agent"
    assert safe["api_key_env"] == "[redacted]"
    assert safe["authorization"] == "[redacted]"


def test_action_classification_is_conservative():
    assert classify_provider_action("chat") == "chat"
    assert classify_provider_action("health") == "health"
    assert classify_provider_action("terminal") == "device_control"
    assert classify_provider_action("unknown-action") == "unknown"
