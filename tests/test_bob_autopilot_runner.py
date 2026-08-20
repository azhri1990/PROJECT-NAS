from pathlib import Path

from runtime.bob_autopilot_runner import run_step


def test_runner_executes_only_allowlisted_steps(tmp_path: Path, monkeypatch):
    calls = []

    class Result:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        return Result()

    monkeypatch.setattr("runtime.bob_autopilot_runner.subprocess.run", fake_run)
    result = run_step("pytest", cwd=tmp_path)

    assert result.ok
    assert calls == [["python", "-m", "pytest", "-q"]]


def test_runner_rejects_arbitrary_shell(tmp_path: Path):
    result = run_step("shell:rm -rf /", cwd=tmp_path)
    assert not result.ok
    assert "allowlist" in result.error.lower()


def test_runner_maps_build_checks_to_fixed_commands(tmp_path: Path, monkeypatch):
    class Result:
        returncode = 0
        stdout = "ok"
        stderr = ""

    captured = []
    monkeypatch.setattr(
        "runtime.bob_autopilot_runner.subprocess.run",
        lambda command, **kwargs: (captured.append(command) or Result()),
    )

    assert run_step("compile", cwd=tmp_path).ok
    assert run_step("diff-check", cwd=tmp_path).ok
    assert captured == [
        ["python", "-m", "compileall", "-q", "runtime", "tests"],
        ["git", "diff", "--check"],
    ]
