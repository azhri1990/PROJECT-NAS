from pathlib import Path


SCRIPT = Path("runtime/bootstrap_bob_android.sh").read_text(encoding="utf-8")


def test_bootstrap_is_fail_closed_and_does_not_start_public_daemon():
    assert 'set -euo pipefail' in SCRIPT
    assert 'PROJECT_BOB_AUTH_TOKEN' in SCRIPT
    assert 'REPLACE_WITH' not in SCRIPT
    assert '0.0.0.0' not in SCRIPT
    assert 'ngrok' not in SCRIPT.lower()
    assert 'cloudflared' not in SCRIPT.lower()


def test_bootstrap_uses_existing_project_runtime():
    assert 'PROJECT_NAS_ROOT' in SCRIPT
    assert 'runtime.doctor' in SCRIPT
