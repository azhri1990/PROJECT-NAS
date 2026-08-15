from __future__ import annotations

import os
from typing import Sequence

from .catalog import configured_provider, default_catalog
from .openai_compatible import OpenAICompatibleProvider
from .providers import Message, ProviderRegistry
from .security import is_allowed_provider_url, redact_provider_metadata


class OmniService:
    """Build and expose only explicitly configured, policy-approved providers."""

    def __init__(self, registry: ProviderRegistry, profiles=None) -> None:
        self.registry = registry
        self.profiles = tuple(profiles or default_catalog())

    @classmethod
    def from_environment(cls) -> "OmniService":
        registry = ProviderRegistry()
        allowed_hosts = {
            value.strip().lower()
            for value in os.environ.get("PROJECT_NAS_OMNI_ALLOWED_HOSTS", "").split(",")
            if value.strip()
        }
        profiles = default_catalog()
        profile_by_name = {profile.name: profile for profile in profiles}

        endpoint_settings = (
            (
                "ollama-local-ai",
                os.environ.get("PROJECT_NAS_OMNI_OLLAMA_URL"),
                os.environ.get("PROJECT_NAS_OMNI_OLLAMA_MODEL", ""),
                os.environ.get("PROJECT_NAS_OMNI_OLLAMA_API_KEY_ENV"),
            ),
            (
                "custom-openai-compatible",
                os.environ.get("PROJECT_NAS_OMNI_COMPAT_URL"),
                os.environ.get("PROJECT_NAS_OMNI_COMPAT_MODEL", ""),
                os.environ.get("PROJECT_NAS_OMNI_COMPAT_API_KEY_ENV"),
            ),
        )

        for profile_name, url, model, key_env in endpoint_settings:
            if not url or not is_allowed_provider_url(url, allowed_hosts):
                continue
            profile = profile_by_name[profile_name]
            config = configured_provider(
                profile,
                base_url=url,
                model=model,
                api_key_env=key_env,
                enabled=True,
            )
            if config is None:
                continue
            registry.register(config, OpenAICompatibleProvider(config))

        return cls(registry, profiles)

    def providers(self) -> list[dict[str, object]]:
        configured = {provider.config.name: provider for provider in self.registry.enabled()}
        result: list[dict[str, object]] = []
        for profile in self.profiles:
            provider = configured.get(profile.name)
            metadata: dict[str, object] = {
                "name": profile.name,
                "display_name": profile.display_name,
                "kind": profile.kind.value,
                "status": profile.status.value,
                "configured": provider is not None,
                "description": profile.description,
            }
            if provider is not None:
                metadata["base_url"] = provider.config.base_url
                metadata["model"] = provider.config.model
            result.append(redact_provider_metadata(metadata))
        return result

    def health(self) -> list[dict[str, object]]:
        return [
            {
                "name": item.name,
                "reachable": item.reachable,
                "authenticated": item.authenticated,
                "latency_ms": item.latency_ms,
                "detail": item.detail,
            }
            for item in self.registry.health_all()
        ]

    def chat(self, provider_name: str, messages: Sequence[Message]):
        provider = self.registry.get(provider_name)
        if provider is None:
            raise KeyError(f"provider not configured: {provider_name}")
        return provider.chat(messages)
