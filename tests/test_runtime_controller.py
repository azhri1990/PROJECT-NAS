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


def test_stop_leaves_external_services_running_without_claiming_ownership(tmp_path):
    env = dict(__import__("os").environ)
    env["PROJECT_NAS_TEST_PID_DIR"] = str(tmp_path)

    result = run_controller("stop", env=env)

    output = (result.stdout + result.stderr).lower()

    assert result.returncode != 0
    assert "externally managed" in output
    assert "controller" not in output
    assert "stopped with errors" in output


def test_stop_reports_ownership_error_when_state_is_incomplete(tmp_path):
    env = dict(__import__("os").environ)
    env["PROJECT_NAS_TEST_PID_DIR"] = str(tmp_path)

    (tmp_path / "memory-injector.pid").write_text("999999\n")

    result = run_controller("stop", env=env)

    output = (result.stdout + result.stderr).lower()

    assert result.returncode != 0
    assert "ownership" in output


def test_status_does_not_report_controller_ownership_without_pid_state(tmp_path):
    env = dict(__import__("os").environ)
    env["PROJECT_NAS_TEST_PID_DIR"] = str(tmp_path)

    result = run_controller("status", env=env)

    assert result.returncode == 0
    assert "Controller" not in result.stdout
