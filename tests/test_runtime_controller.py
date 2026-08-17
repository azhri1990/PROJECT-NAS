import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "runtime" / "project-nas.sh"


def run_controller(*args, env=None):
    return subprocess.run(
        [str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=env,
    )


def test_stop_does_not_claim_stopped_when_owned_service_state_is_missing(tmp_path):
    env = dict(__import__("os").environ)
    env["PROJECT_NAS_TEST_PID_DIR"] = str(tmp_path)

    result = run_controller("stop", env=env)

    assert result.returncode != 0
    assert "STOPPED" not in result.stdout
    assert "ownership" in (result.stdout + result.stderr).lower()


def test_status_does_not_report_controller_ownership_without_pid_state(tmp_path):
    env = dict(__import__("os").environ)
    env["PROJECT_NAS_TEST_PID_DIR"] = str(tmp_path)

    result = run_controller("status", env=env)

    assert result.returncode == 0
    assert "Controller" not in result.stdout
