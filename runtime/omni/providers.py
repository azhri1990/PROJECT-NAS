from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Mapping, Sequence

from .models import ChatResult, ProviderConfig, ProviderHealth


Message = Mapping[str, object]


class AIProvider(ABC):
    """Minimal provider contract used by the Omni router."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    def health(self) -> ProviderHealth:
        raise NotImplementedError

    @abstractmethod
    def chat(self, messages: Sequence[Message]) -> ChatResult:
        raise NotImplementedError


class ProviderRegistry:
    """In-memory registry; policy decides which providers are enabled."""

    def __init__(self) -> None:
        self._providers: dict[str, tuple[ProviderConfig, AIProvider]] = {}

    def register(self, config: ProviderConfig, provider: AIProvider) -> None:
        if config.name != provider.config.name:
            raise ValueError("provider config and implementation names must match")
        if config.name in self._providers:
            raise ValueError(f"provider already registered: {config.name}")
        self._providers[config.name] = (config, provider)

    def enabled(self) -> Iterable[AIProvider]:
        for config, provider in self._providers.values():
            if config.enabled:
                yield provider

    def get(self, name: str) -> AIProvider | None:
        entry = self._providers.get(name)
        return entry[1] if entry else None

    def health_all(self) -> list[ProviderHealth]:
        results: list[ProviderHealth] = []
        for provider in self.enabled():
            results.append(provider.health())
        return results
