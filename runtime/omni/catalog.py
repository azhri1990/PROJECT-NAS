from __future__ import annotations

from .models import ProviderConfig, ProviderKind, ProviderProfile, ProviderStatus


_PROFILES = (
    ProviderProfile(
        name="ollama-local-ai",
        display_name="Ollama Local AI",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        status=ProviderStatus.SUPPORTED,
        description="Android local-network OpenAI-compatible LLM proxy.",
        default_base_url="http://127.0.0.1:11434/v1",
    ),
    ProviderProfile(
        name="custom-openai-compatible",
        display_name="Custom OpenAI-Compatible Endpoint",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        status=ProviderStatus.SUPPORTED,
        description="Generic adapter for a verified OpenAI-compatible server, including a separately operated Hermes API server.",
    ),
    ProviderProfile(
        name="hermes-agent",
        display_name="Hermes Agent - Android",
        kind=ProviderKind.DEVICE_AGENT,
        status=ProviderStatus.OPTIONAL,
        description="Android agent with terminal, code execution, memory, and beta PC companion; no direct PROJECT-NAS API is assumed.",
    ),
    ProviderProfile(
        name="codex-mobile",
        display_name="Codex Mobile",
        kind=ProviderKind.DEVICE_AGENT,
        status=ProviderStatus.OPTIONAL,
        description="Browser/app-server bridge for Codex workflows; no PROJECT-NAS execution contract assumed.",
    ),
    ProviderProfile(
        name="pocketpal",
        display_name="PocketPal AI",
        kind=ProviderKind.LOCAL_ONLY,
        status=ProviderStatus.UNVERIFIED,
        description="On-device GGUF inference; no remote PROJECT-NAS API contract assumed.",
    ),
    ProviderProfile(
        name="offlinegpt",
        display_name="OfflineGPT",
        kind=ProviderKind.LOCAL_ONLY,
        status=ProviderStatus.UNVERIFIED,
        description="On-device offline inference; no remote PROJECT-NAS API contract assumed.",
    ),
    ProviderProfile(
        name="hermes-relay",
        display_name="Hermes-Relay",
        kind=ProviderKind.DEVICE_AGENT,
        status=ProviderStatus.OPTIONAL,
        description="Android client/relay surface for a configured Hermes instance; not a model provider.",
    ),
)


def default_catalog() -> tuple[ProviderProfile, ...]:
    return _PROFILES


def configured_provider(
    profile: ProviderProfile,
    *,
    base_url: str | None = None,
    model: str = "",
    api_key_env: str | None = None,
    enabled: bool = False,
) -> ProviderConfig | None:
    """Build an active provider config only for explicitly supported profiles."""
    if profile.status is not ProviderStatus.SUPPORTED:
        return None
    resolved_url = base_url or profile.default_base_url
    if not resolved_url:
        return None
    return ProviderConfig(
        name=profile.name,
        kind=profile.kind,
        base_url=resolved_url,
        api_key_env=api_key_env,
        model=model,
        enabled=enabled,
    )
