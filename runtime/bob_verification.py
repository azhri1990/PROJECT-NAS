from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class VerificationState(str, Enum):
    NOT_TRIGGERED = "NOT_TRIGGERED"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    VERIFIED = "VERIFIED"


@dataclass(frozen=True)
class VerificationResult:
    state: VerificationState


def evaluate_verification(expected_sha: str, run: dict[str, Any] | None) -> VerificationResult:
    """Evaluate CI evidence for one exact repository revision."""
    if run is None or run.get("sha") != expected_sha:
        return VerificationResult(VerificationState.NOT_TRIGGERED)

    if run.get("status") != "completed":
        return VerificationResult(VerificationState.RUNNING)

    if run.get("conclusion") == "success":
        return VerificationResult(VerificationState.VERIFIED)

    return VerificationResult(VerificationState.FAILED)
