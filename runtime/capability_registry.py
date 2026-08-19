"""Validation and loading for the advisory PROJECT-NAS app capability registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CLASSIFICATIONS = {"CORE", "WORKER", "TOOL", "BACKUP", "PERSONAL", "IGNORE"}
DISPOSITIONS = {"KEEP", "OPTIONAL", "BACKUP_ONLY", "IGNORE", "REMOVE_CANDIDATE"}
PLATFORM_ROLES = {
    "ANDROID_EDGE",
    "TABLET_EDGE",
    "PC_BUILD",
    "GITHUB_SOURCE",
    "NAS_RUNTIME",
}
REQUIRED_FIELDS = {
    "name",
    "classification",
    "capabilities",
    "platform_roles",
    "integration",
    "security",
    "disposition",
    "reason",
}
FORBIDDEN_AUTHORITY_FIELDS = {
    "permissions",
    "policy_override",
    "credentials",
    "secrets",
    "api_key",
    "bearer_token",
    "executable",
    "shell_command",
    "filesystem_write",
    "network_access",
}


def validate_capability_registry(records: list[dict[str, Any]]) -> list[str]:
    """Return deterministic validation errors for advisory registry records."""
    errors: list[str] = []
    seen: set[str] = set()

    if not isinstance(records, list):
        return ["registry must be a list"]

    for index, record in enumerate(records):
        prefix = f"record[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{prefix}: record must be an object")
            continue

        missing = sorted(REQUIRED_FIELDS - record.keys())
        errors.extend(f"{prefix}: missing required field {field!r}" for field in missing)

        name = record.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{prefix}: name must be a non-empty string")
        elif name in seen and "duplicate inventory entry" not in str(record.get("reason", "")).lower():
            errors.append(f"{prefix}: duplicate canonical name {name!r}")
        else:
            seen.add(name)

        classification = record.get("classification")
        if classification not in CLASSIFICATIONS:
            errors.append(f"{prefix}: invalid classification {classification!r}")

        disposition = record.get("disposition")
        if disposition not in DISPOSITIONS:
            errors.append(f"{prefix}: invalid disposition {disposition!r}")

        capabilities = record.get("capabilities")
        if not isinstance(capabilities, list) or not all(isinstance(item, str) for item in capabilities):
            errors.append(f"{prefix}: capabilities must be a list of strings")

        roles = record.get("platform_roles")
        if not isinstance(roles, list) or not all(role in PLATFORM_ROLES for role in roles):
            errors.append(f"{prefix}: platform_roles must contain only known role labels")

        for field in sorted(FORBIDDEN_AUTHORITY_FIELDS.intersection(record)):
            errors.append(f"{prefix}: forbidden authority field {field!r}")

    return errors


def load_capability_registry(path: str | Path) -> list[dict[str, Any]]:
    """Load and validate a capability registry from a local JSON file."""
    registry_path = Path(path)
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("capability registry must contain a JSON list")

    errors = validate_capability_registry(payload)
    if errors:
        raise ValueError("invalid capability registry: " + "; ".join(errors))
    return payload
