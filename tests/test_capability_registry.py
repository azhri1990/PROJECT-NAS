import json
from pathlib import Path

import pytest

from runtime.capability_registry import load_capability_registry, validate_capability_registry


REGISTRY = Path(__file__).parents[1] / "docs" / "capabilities" / "app-capability-matrix.json"


def test_canonical_registry_exists_and_is_valid():
    records = load_capability_registry(REGISTRY)
    assert records
    assert validate_capability_registry(records) == []


def test_registry_rejects_unknown_classification():
    records = [{
        "name": "Example",
        "classification": "SUPERPOWER",
        "capabilities": ["test"],
        "platform_roles": ["PC_BUILD"],
        "integration": "none",
        "security": "low",
        "disposition": "IGNORE",
        "reason": "test",
    }]
    errors = validate_capability_registry(records)
    assert any("classification" in error for error in errors)


def test_registry_rejects_missing_required_field():
    records = [{
        "name": "Example",
        "classification": "TOOL",
        "capabilities": ["test"],
        "platform_roles": ["PC_BUILD"],
        "integration": "none",
        "security": "low",
        "disposition": "OPTIONAL",
    }]
    errors = validate_capability_registry(records)
    assert any("reason" in error for error in errors)


def test_registry_rejects_duplicate_canonical_names():
    record = {
        "name": "Example",
        "classification": "TOOL",
        "capabilities": ["test"],
        "platform_roles": ["PC_BUILD"],
        "integration": "none",
        "security": "low",
        "disposition": "OPTIONAL",
        "reason": "test",
    }
    errors = validate_capability_registry([record, dict(record)])
    assert any("duplicate" in error.lower() for error in errors)


def test_registry_rejects_permission_escalation_fields():
    record = {
        "name": "Example",
        "classification": "TOOL",
        "capabilities": ["test"],
        "platform_roles": ["PC_BUILD"],
        "integration": "none",
        "security": "low",
        "disposition": "OPTIONAL",
        "reason": "test",
        "permissions": ["filesystem.write"],
    }
    errors = validate_capability_registry([record])
    assert any("permissions" in error.lower() for error in errors)


def test_registry_json_is_an_object_list():
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert all(isinstance(record, dict) for record in payload)
