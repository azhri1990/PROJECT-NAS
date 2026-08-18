from pathlib import Path
import subprocess


RECOVERY = Path("runtime/recovery.sh")
SELFTEST = Path("runtime/recovery-selftest.sh")


def test_recovery_supports_controlled_failure_injection_contract():
    text = RECOVERY.read_text(encoding="utf-8")
    assert "Runtime unhealthy; invoking existing controller start path" in text
    assert "Runtime recovery verified" in text


def test_recovery_selftest_exists_and_is_bash():
    text = SELFTEST.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/bash")
    assert "PROJECT_NAS_RECOVERY_SELFTEST_STATE" in text
    assert "Controlled recovery simulation passed" in text


def test_recovery_selftest_runs_without_real_services():
    result = subprocess.run(
        ["bash", str(SELFTEST)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Controlled recovery simulation passed" in result.stdout


def test_recovery_does_not_introduce_paid_services():
    for path in (RECOVERY, SELFTEST):
        text = path.read_text(encoding="utf-8").lower()
        for marker in ("openai_api_key", "anthropic_api_key", "aws_access_key", "stripe"):
            assert marker not in text
