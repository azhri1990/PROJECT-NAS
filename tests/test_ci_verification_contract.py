from pathlib import Path


def test_runtime_integration_triggers_bob_branches():
    workflow = Path(".github/workflows/runtime-integration.yml").read_text(encoding="utf-8")
    assert "'bob/**'" in workflow
