from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable


class VerificationState(str, Enum):
    NOT_TRIGGERED = "NOT_TRIGGERED"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    VERIFIED = "VERIFIED"


@dataclass(frozen=True)
class VerificationResult:
    state: VerificationState


def select_exact_sha_run(expected_sha: str, runs: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    """Select workflow evidence only when GitHub reports the exact head SHA."""
    if not isinstance(expected_sha, str) or not expected_sha.strip():
        raise ValueError("expected_sha must not be empty")
    for run in runs:
        if not isinstance(run, dict):
            continue
        reported_sha = run.get("head_sha", run.get("sha"))
        if reported_sha == expected_sha:
            return run
    return None


def evaluate_verification(expected_sha: str, run: dict[str, Any] | None) -> VerificationResult:
    """Evaluate CI evidence for one exact repository revision."""
    if run is None:
        return VerificationResult(VerificationState.NOT_TRIGGERED)

    reported_sha = run.get("head_sha", run.get("sha"))
    if reported_sha != expected_sha:
        return VerificationResult(VerificationState.NOT_TRIGGERED)

    if run.get("status") != "completed":
        return VerificationResult(VerificationState.RUNNING)

    if run.get("conclusion") == "success":
        return VerificationResult(VerificationState.VERIFIED)

    return VerificationResult(VerificationState.FAILED)
