"""Advisory worker selection for PROJECT-NAS capability metadata."""

from __future__ import annotations

from typing import Any

EXCLUDED_CLASSIFICATIONS = {"PERSONAL", "IGNORE"}
EXCLUDED_DISPOSITIONS = {"IGNORE", "REMOVE_CANDIDATE"}
CLASSIFICATION_PRIORITY = {"CORE": 0, "BACKUP": 1, "WORKER": 2, "TOOL": 3}


def select_workers(
    records: list[dict[str, Any]],
    capability: str,
    platform_role: str | None = None,
) -> list[dict[str, Any]]:
    """Return advisory candidates; never grants or executes permissions."""
    normalized = capability.strip().lower()
    candidates: list[dict[str, Any]] = []

    for record in records:
        if record.get("classification") in EXCLUDED_CLASSIFICATIONS:
            continue
        if record.get("disposition") in EXCLUDED_DISPOSITIONS:
            continue
        capabilities = {str(item).strip().lower() for item in record.get("capabilities", [])}
        if normalized not in capabilities:
            continue
        if platform_role and platform_role not in record.get("platform_roles", []):
            continue
        candidates.append(record)

    return sorted(
        candidates,
        key=lambda record: (
            CLASSIFICATION_PRIORITY.get(record.get("classification"), 99),
            str(record.get("name", "")).casefold(),
        ),
    )
