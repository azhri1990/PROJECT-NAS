"""Bounded local-only model discovery and fallback routing for PROJECT-NAS."""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlparse

import requests

from runtime.resource_aware_model_router import ResourceAwareModelRouter, TaskComplexity

DEFAULT_PREFERRED_MODELS = ("llama3.2:3b", "llama3.2:1b", "llama3.1:8b")


@dataclass(frozen=True)
class ModelRoute:
    configured: str
    selected: str | None
    available: tuple[str, ...]
    fallback: bool


class LocalModelRouter:
    """Discover and select only loopback Ollama models; never uses remote hosts."""

    def __init__(
        self,
        configured_model: str,
        base_url: str = "http://127.0.0.1:11434",
        preferred_models: tuple[str, ...] = DEFAULT_PREFERRED_MODELS,
        discovery_timeout: float = 3.0,
    ) -> None:
        if not isinstance(configured_model, str) or not configured_model.strip():
            raise ValueError("configured_model must be a non-empty string")
        if discovery_timeout <= 0:
            raise ValueError("discovery_timeout must be positive")
        self.configured_model = configured_model.strip()
        self.base_url = base_url.rstrip("/")
        self.preferred_models = tuple(dict.fromkeys((self.configured_model, *preferred_models)))
        self.discovery_timeout = discovery_timeout

    @staticmethod
    def is_loopback_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                return False
            hostname = parsed.hostname.lower()
            if hostname == "localhost":
                return True
            try:
                return ip_address(hostname).is_loopback
            except ValueError:
                return False
        except (TypeError, ValueError):
            return False

    def discover(self) -> tuple[str, ...]:
        if not self.is_loopback_url(self.base_url):
            return ()
        try:
            response = requests.get(
                f"{self.base_url}/api/tags", timeout=self.discovery_timeout
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError, TypeError):
            return ()
        models = {
            item.get("name")
            for item in payload.get("models", [])
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        return tuple(sorted(name for name in models if name))

    def route(self, available: tuple[str, ...] | list[str] | None = None) -> ModelRoute:
        names = tuple(sorted({name for name in (available or ()) if isinstance(name, str) and name}))
        selected = next((name for name in self.preferred_models if name in names), None)
        return ModelRoute(
            configured=self.configured_model,
            selected=selected,
            available=names,
            fallback=selected is not None and selected != self.configured_model,
        )

    def discover_route(self) -> ModelRoute:
        return self.route(self.discover())

    def resource_aware_route(self, complexity: TaskComplexity) -> Any:
        """Select a local model using live resource pressure without changing URL policy."""
        router = ResourceAwareModelRouter(
            self.configured_model,
            preferred_models=self.preferred_models,
        )
        return router.route(available=self.discover(), complexity=complexity)

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        timeout: float = 75.0,
        num_predict: int = 128,
    ) -> dict[str, Any]:
        if not isinstance(prompt, str) or not prompt:
            raise ValueError("prompt must be a non-empty string")
        if not self.is_loopback_url(self.base_url):
            raise ValueError("Ollama URL must point to a local loopback address")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if not isinstance(num_predict, int) or isinstance(num_predict, bool) or not 1 <= num_predict <= 4096:
            raise ValueError("num_predict must be an integer from 1 to 4096")

        selected = model or self.configured_model
        payload = {
            "model": selected,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": num_predict},
        }
        response = requests.post(
            f"{self.base_url}/api/generate", json=payload, timeout=timeout
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError("Ollama returned a non-object response")
        return result

    def generate_with_fallback(
        self,
        prompt: str,
        *,
        timeout: float = 75.0,
        num_predict: int = 128,
    ) -> tuple[dict[str, Any], ModelRoute]:
        try:
            return self.generate(prompt, timeout=timeout, num_predict=num_predict), self.route((self.configured_model,))
        except requests.HTTPError as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status not in {400, 404}:
                raise
        except (requests.ConnectionError, requests.Timeout):
            pass
        route = self.discover_route()
        if route.selected is None:
            raise RuntimeError("configured local model is unavailable and no fallback model was found")
        return self.generate(prompt, model=route.selected, timeout=timeout, num_predict=num_predict), route
