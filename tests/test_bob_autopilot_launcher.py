from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_launcher_runs_daemon_as_package_module():
    launcher = (ROOT / "tools" / "start-bob-autopilot.ps1").read_text(encoding="utf-8")
    assert "-m" in launcher
    assert "runtime.bob_autopilot_daemon" in launcher


def test_daemon_uses_package_imports():
    daemon = (ROOT / "runtime" / "bob_autopilot_daemon.py").read_text(encoding="utf-8")
    assert "from .bob_autopilot_loop import AutopilotLoop" in daemon
