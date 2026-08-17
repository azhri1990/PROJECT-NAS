from pathlib import Path


def test_runtime_certification_gate_declares_required_checks():
    workflow = Path(".github/workflows/runtime-integration.yml").read_text(encoding="utf-8")
    required = (
        "Full regression",
        "Runtime controller smoke",
        "Static runtime verification",
        "Doctor diagnostics",
    )
    for marker in required:
        assert marker in workflow


def test_runtime_certification_does_not_require_paid_services():
    workflow = Path(".github/workflows/runtime-integration.yml").read_text(encoding="utf-8").lower()
    assert "openai_api_key" not in workflow
    assert "anthropic_api_key" not in workflow
    assert "aws_access_key" not in workflow
