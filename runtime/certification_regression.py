"""Deterministic regression detection for PROJECT-NAS certification records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CertificationComparison:
    regression: bool
    issues: list[str]


def compare_certifications(
    baseline: dict[str, Any] | None,
    current: dict[str, Any],
) -> CertificationComparison:
    """Compare a current certification against the last known GREEN baseline."""
    if baseline is None:
        return CertificationComparison(False, [])

    required = {"result", "tests", "gates"}
    if not required.issubset(baseline):
        return CertificationComparison(True, ["Baseline certification is incomplete"])

    issues: list[str] = []
    try:
        baseline_tests = int(baseline["tests"])
        current_tests = int(current.get("tests", 0))
        if baseline_tests < 0 or current_tests < 0:
            raise ValueError
    except (TypeError, ValueError):
        issues.append("Certification test count is invalid")
    else:
        if current_tests < baseline_tests:
            issues.append(f"Regression suite tests dropped: {baseline_tests} -> {current_tests}")

    baseline_gates = baseline.get("gates")
    current_gates = current.get("gates")
    if not isinstance(baseline_gates, dict) or not isinstance(current_gates, dict):
        issues.append("Certification gate data is invalid")
    else:
        for name, baseline_status in baseline_gates.items():
            current_status = current_gates.get(name)
            if baseline_status == "GREEN" and current_status == "RED":
                issues.append(f"Gate failed: {name}")
            elif baseline_status == "GREEN" and current_status is None:
                issues.append(f"Gate missing: {name}")

    if current.get("result") == "RED":
        issues.append("Current certification is RED")

    return CertificationComparison(bool(issues), issues)
