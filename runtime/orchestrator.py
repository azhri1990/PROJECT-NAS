"""Bounded local intent routing for PROJECT-NAS."""

from __future__ import annotations

from typing import Any

from runtime.tool_gateway import ToolGateway, build_default_gateway


_INTENT_TO_TOOL = {
    "health": ("status.health", {}),
    "progress": ("status.progress", {}),
    "memory": ("memory.read", {}),
    "prompt": ("prompt.get", {}),
}


class IntentRouter:
    """Route a fixed set of read-only intents through the ToolGateway."""

    def __init__(self, gateway: ToolGateway | None = None) -> None:
        self.gateway = gateway or build_default_gateway()

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


def build_default_router() -> IntentRouter:
    return IntentRouter()
