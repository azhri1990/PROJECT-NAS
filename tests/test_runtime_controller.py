import os
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


def test_stop_reports_external_services_without_claiming_ownership(tmp_path):
    env = dict(os.environ)
    env["PROJECT_NAS_TEST_PID_DIR"] = str(tmp_path / "pids")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_curl = fake_bin / "curl"
    fake_curl.write_text("#!/bin/sh\ncase \"$*\" in\n  *5001/health*|*5000/health*|*11434/api/tags*) exit 0 ;;\n  *) exit 1 ;;\nesac\n")
    fake_curl.chmod(0o755)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = run_controller("stop", env=env)
    output = (result.stdout + result.stderr).lower()

    assert result.returncode != 0
    assert "externally managed" in output
    assert "stopped with errors" in output
    assert "controller" not in output


def test_stop_succeeds_when_no_services_are_running(tmp_path):
    env = dict(os.environ)
    env["PROJECT_NAS_TEST_PID_DIR"] = str(tmp_path / "pids")
    # Isolate this test from any real PROJECT-NAS runtime that may be running
    # on the developer/CI host. The behavior under test is the no-service path,
    # not whether an unrelated local service happens to answer its default port.
    env["PROJECT_NAS_BACKEND_HEALTH_URL"] = "http://127.0.0.1:1/health"
    env["PROJECT_NAS_MEMORY_HEALTH_URL"] = "http://127.0.0.1:1/health"
    env["PROJECT_NAS_OLLAMA_BASE_URL"] = "http://127.0.0.1:1"

    result = run_controller("stop", env=env)
    output = (result.stdout + result.stderr).lower()

    assert result.returncode == 0
    assert "not running under controller ownership" in output
    assert "stopped with errors" not in output


def test_stop_reports_ownership_error_when_state_is_incomplete(tmp_path):
    env = dict(os.environ)
    env["PROJECT_NAS_TEST_PID_DIR"] = str(tmp_path)

    (tmp_path / "memory-injector.pid").write_text("999999\n")

    result = run_controller("stop", env=env)
    output = (result.stdout + result.stderr).lower()

    assert result.returncode != 0
    assert "ownership" in output


def test_status_does_not_report_controller_ownership_without_pid_state(tmp_path):
    env = dict(os.environ)
    env["PROJECT_NAS_TEST_PID_DIR"] = str(tmp_path)

    result = run_controller("status", env=env)

    assert result.returncode == 0
    assert "Controller" not in result.stdout
