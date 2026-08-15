from __future__ import annotations

import os
import time
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse, urlunparse

import requests

from .models import ChatResult, ProviderConfig, ProviderHealth
from .providers import AIProvider, Message


class ProviderError(RuntimeError):
    """Safe provider error that never contains credentials or response bodies."""


class OpenAICompatibleProvider(AIProvider):
    """Adapter for local or self-hosted OpenAI-compatible HTTP endpoints."""

    def __init__(self, config: ProviderConfig, session: requests.Session | None = None) -> None:
        super().__init__(config)
        self.session = session or requests.Session()

    def _api_key(self) -> str | None:
        if not self.config.api_key_env:
            return None
        return os.environ.get(self.config.api_key_env)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        key = self._api_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def _root_url(self) -> str:
        parsed = urlparse(self.config.base_url.rstrip("/"))
        path = parsed.path.rstrip("/")
        if path.endswith("/v1"):
            path = path[:-3]
        return urlunparse((parsed.scheme, parsed.netloc, path, "", "", "")).rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"

    def health(self) -> ProviderHealth:
        started = time.perf_counter()
        try:
            response = self.session.get(
                f"{self._root_url()}/health",
                headers=self._headers(),
                timeout=self.config.timeout_seconds,
            )
            if response.status_code == 404:
                response = self.session.get(
                    self._url("models"),
                    headers=self._headers(),
                    timeout=self.config.timeout_seconds,
                )
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            if response.status_code == 401:
                return ProviderHealth(self.config.name, True, False, latency_ms, "authentication rejected")
            if 200 <= response.status_code < 300:
                return ProviderHealth(self.config.name, True, True if self._api_key() else None, latency_ms, "ok")
            return ProviderHealth(
                self.config.name,
                True,
                None,
                latency_ms,
                f"provider returned HTTP {response.status_code}",
            )
        except requests.RequestException as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            return ProviderHealth(self.config.name, False, None, latency_ms, exc.__class__.__name__)

    def chat(self, messages: Sequence[Message]) -> ChatResult:
        normalized: list[dict[str, Any]] = []
        total_chars = 0
        for message in messages:
            role = str(message.get("role", ""))
            content = message.get("content", "")
            if role not in {"system", "user", "assistant", "tool"}:
                raise ProviderError("unsupported message role")
            if not isinstance(content, str):
                raise ProviderError("message content must be text")
            total_chars += len(content)
            if total_chars > self.config.max_input_chars:
                raise ProviderError("input exceeds provider limit")
            normalized.append({"role": role, "content": content})

        payload: dict[str, Any] = {"messages": normalized}
        if self.config.model:
            payload["model"] = self.config.model

        started = time.perf_counter()
        try:
            response = self.session.post(
                self._url("chat/completions"),
                headers=self._headers(),
                json=payload,
                timeout=self.config.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise ProviderError(f"provider request failed: {exc.__class__.__name__}") from exc

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        if response.status_code == 401:
            raise ProviderError("provider authentication rejected")
        if response.status_code >= 400:
            raise ProviderError(f"provider returned HTTP {response.status_code}")

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError("provider returned an invalid chat response") from exc

        if not isinstance(content, str):
            raise ProviderError("provider returned non-text content")

        return ChatResult(
            text=content,
            provider=self.config.name,
            model=str(payload.get("model", "")),
            latency_ms=latency_ms,
        )
