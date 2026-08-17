from pathlib import Path


CERTIFIER = Path("runtime/project-nas-certify.sh")


def test_runtime_certifier_exists_and_is_bash():
    text = CERTIFIER.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/bash")
    assert "CERTIFICATION: GREEN" in text
    assert "CERTIFICATION: RED" in text


def test_runtime_certifier_has_all_required_gates():
    text = CERTIFIER.read_text(encoding="utf-8")
    for marker in (
        'runtime/doctor.py',
        'PROJECT_NAS_BACKEND_HEALTH_URL',
        'PROJECT_NAS_MEMORY_HEALTH_URL',
        'PROJECT_NAS_OLLAMA_BASE_URL',
        'compileall',
        'bash -n',
        'git -C "$PROJECT_ROOT" diff --check',
        'python -m pytest -q tests',
    ):
        assert marker in text


def test_runtime_certifier_has_no_paid_service_dependency():
    text = CERTIFIER.read_text(encoding="utf-8").lower()
    for marker in ("openai_api_key", "anthropic_api_key", "aws_access_key", "stripe"):
        assert marker not in text
