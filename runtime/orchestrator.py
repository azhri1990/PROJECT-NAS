"""Bounded local intent routing for PROJECT-NAS.

This module maps a fixed set of user-facing read intents to the existing
ToolGateway. It performs no privileged execution and never constructs dynamic
tool names from user input.
"""

from __future__ import annotations

from typing import Any

from runtime.tool_gateway import ToolGateway, build_default_gateway


_INTENT_TO_TOOL = {
    "health": ("status.health", {}),
    "progress": ("status.progress", None),
    "memory": ("memory.read", None),
    "prompt": ("prompt.get", None),
}


class IntentRouter:
    """Route only explicitly allowlisted read intents through ToolGateway."""

    def __init__(self, gateway: ToolGateway | None = None) -> None:
        self.gateway = gateway or build_default_gateway()

    def handle(self, intent: str, payload: dict[str, Any] | None = None) -> Any:
        if not isinstance(intent, str):
            raise ValueError("intent must be a string")
        normalized = intent.strip().lower()
        if normalized not in _INTENT_TO_TOOL:
            raise PermissionError("intent denied")

        tool_name, default_payload = _INTENT_TO_TOOL[normalized]
        if payload is None:
            payload = default_payload if default_payload is not None else {}
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        return self.gateway.execute(tool_name, payload)


def build_default_router() -> IntentRouter:
    return IntentRouter()
