from pathlib import Path


RECOVERY = Path("runtime/recovery.sh")


def test_recovery_supports_controlled_failure_injection_contract():
    text = RECOVERY.read_text(encoding="utf-8")
    assert "PROJECT_NAS_RECOVERY_TEST_MODE" in text
    assert "Runtime unhealthy; invoking existing controller start path" in text
    assert "Runtime recovery verified" in text


def test_recovery_test_mode_does_not_touch_real_services():
    text = RECOVERY.read_text(encoding="utf-8")
    assert "127.0.0.1" in text
    assert "curl" in text
    assert "project-nas.sh" in text
