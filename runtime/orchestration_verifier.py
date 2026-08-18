"""Fail-closed post-execution verification for JARVIS tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    reason: str


def verify_result(tool_name: str, result: Any) -> VerificationResult:
    """Verify only known deterministic result contracts; unknown tools fail closed."""
    if tool_name == "status.health":
        if isinstance(result, dict) and result.get("status") == "healthy":
            return VerificationResult(True, "health result verified")
        return VerificationResult(False, "health result did not contain healthy status")
    return VerificationResult(False, f"no verification contract for tool: {tool_name}")
