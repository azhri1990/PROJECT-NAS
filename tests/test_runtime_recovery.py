from pathlib import Path


CONTROLLER = Path("runtime/project-nas.sh")
CERTIFIER = Path("runtime/project-nas-certify.sh")


def test_runtime_controller_exposes_recovery_command():
    text = CONTROLLER.read_text(encoding="utf-8")
    assert "recover" in text
    assert "recover_runtime()" in text


def test_recovery_is_health_aware_and_uses_existing_start_path():
    text = CONTROLLER.read_text(encoding="utf-8")
    assert 'BACKEND_HEALTH_URL' in text
    assert 'start_runtime' in text
    assert 'recover_runtime()' in text


def test_certifier_uses_recovery_path_before_certification():
    text = CERTIFIER.read_text(encoding="utf-8")
    assert '"$CONTROLLER" recover' in text


def test_recovery_does_not_introduce_paid_services():
    for path in (CONTROLLER, CERTIFIER):
        text = path.read_text(encoding="utf-8").lower()
        for marker in ("openai_api_key", "anthropic_api_key", "aws_access_key", "stripe"):
            assert marker not in text
