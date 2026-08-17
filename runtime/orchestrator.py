"""Bounded local intent and model orchestration for PROJECT-NAS."""

from __future__ import annotations

import os
from typing import Any

from runtime.context_budget import ContextBudget, compose_context
from runtime.local_model_router import LocalModelRouter, ModelRoute
from runtime.tool_gateway import ToolGateway, build_default_gateway


_INTENT_TO_TOOL = {
    "health": ("status.health", {}),
    "progress": ("status.progress", {}),
    "memory": ("memory.read", {}),
    "prompt": ("prompt.get", {}),
}

DEFAULT_MODEL = "llama3.2:3b"
MAX_USER_INPUT_CHARS = 8000


class IntentRouter:
    """Route fixed read-only intents and bounded local-model requests."""

    def __init__(self, gateway: ToolGateway | None = None, model_router: LocalModelRouter | None = None) -> None:
        self.gateway = gateway or build_default_gateway()
        self.model_router = model_router or LocalModelRouter(
            configured_model=os.environ.get("PROJECT_NAS_OLLAMA_MODEL", DEFAULT_MODEL),
            base_url=os.environ.get("PROJECT_NAS_OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        )

    def handle(self, intent: str, payload: dict[str, Any] | None = None) -> Any:
        if not isinstance(intent, str):
            raise ValueError("intent must be a string")
        normalized = intent.strip().lower()
        if normalized not in _INTENT_TO_TOOL:
            raise PermissionError("intent denied")
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        tool_name, _ = _INTENT_TO_TOOL[normalized]
        return self.gateway.execute(tool_name, payload)

    @staticmethod
    def _memory_text(result: Any) -> str:
        if not isinstance(result, dict):
            return ""
        memories = result.get("memories", [])
        if not isinstance(memories, list):
            return ""
        parts: list[str] = []
        for memory in memories:
            if not isinstance(memory, dict):
                continue
            document = str(memory.get("document", "")).strip()
            if document:
                parts.append(document)
        return "\n\n".join(parts)

    def generate_response(
        self,
        user_input: str,
        *,
        memory_query: str | None = None,
        system_prompt: str | None = None,
        max_chars: int = 12000,
        num_predict: int = 128,
        timeout: float = 75.0,
    ) -> tuple[dict[str, Any], ModelRoute, bool]:
        """Build bounded context through the gateway and generate with a local model."""
        if not isinstance(user_input, str) or not user_input.strip():
            raise ValueError("user_input must be a non-empty string")
        if len(user_input) > MAX_USER_INPUT_CHARS:
            raise ValueError(f"user_input exceeds maximum length of {MAX_USER_INPUT_CHARS} characters")
        if not isinstance(max_chars, int) or isinstance(max_chars, bool):
            raise ValueError("max_chars must be an integer")

        if system_prompt is None:
            prompt_result = self.handle("prompt", {"max_chars": min(max_chars, 12000)})
            system_prompt = str(prompt_result.get("content", "")) if isinstance(prompt_result, dict) else ""

        memory_result = self.handle("memory", {"query": memory_query, "limit": 5})
        memory_text = self._memory_text(memory_result)
        context, truncated = compose_context(
            system_prompt or "You are PROJECT-NAS, a local-first personal operating system.",
            memory_text,
            user_input.strip(),
            budget=ContextBudget(max_chars=max_chars),
        )
        result, route = self.model_router.generate_with_fallback(
            context,
            timeout=timeout,
            num_predict=num_predict,
        )
        return result, route, truncated


def build_default_router() -> IntentRouter:
    return IntentRouter()
