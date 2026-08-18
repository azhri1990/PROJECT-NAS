from pathlib import Path


CONTROLLER = Path("runtime/project-nas.sh")
CERTIFIER = Path("runtime/project-nas-certify.sh")
RECOVERY = Path("runtime/recovery.sh")


def test_runtime_recovery_helper_exists_and_is_bash():
    text = RECOVERY.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/bash")
    assert '"$CONTROLLER" start' in text


def test_recovery_checks_all_local_services():
    text = RECOVERY.read_text(encoding="utf-8")
    for marker in (
        "BACKEND_HEALTH_URL",
        "MEMORY_HEALTH_URL",
        "OLLAMA_HEALTH_URL",
        "runtime_healthy",
    ):
        assert marker in text


def test_recovery_is_health_aware_and_verifies_recovery():
    text = RECOVERY.read_text(encoding="utf-8")
    assert 'Runtime unhealthy' in text
    assert 'Runtime recovery verified' in text


def test_certifier_uses_recovery_helper_before_certification():
    text = CERTIFIER.read_text(encoding="utf-8")
    assert 'RECOVERY="$SCRIPT_DIR/recovery.sh"' in text
    assert '"$RECOVERY"' in text


def test_recovery_does_not_introduce_paid_services():
    for path in (CONTROLLER, CERTIFIER, RECOVERY):
        text = path.read_text(encoding="utf-8").lower()
        for marker in ("openai_api_key", "anthropic_api_key", "aws_access_key", "stripe"):
            assert marker not in text
