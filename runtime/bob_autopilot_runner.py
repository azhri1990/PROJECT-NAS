"""Allowlisted local execution primitives for constrained PROJECT-BOB autopilot."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StepResult:
    ok: bool
    step: str
    output: str = ""
    error: str = ""
    returncode: int = 0


_COMMANDS: dict[str, list[str]] = {
    "diff-check": ["git", "diff", "--check"],
}


def _python_command(*args: str) -> list[str]:
    """Run Python steps with the interpreter executing BOB."""
    return [sys.executable, *args]


def _command_for_step(step: str) -> list[str] | None:
    if step == "pytest":
        return _python_command("-m", "pytest", "-q")
    if step == "compile":
        return _python_command("-m", "compileall", "-q", "runtime", "tests")
    return _COMMANDS.get(step)


def run_step(step: str, *, cwd: Path | str = ".") -> StepResult:
    """Execute one fixed, non-shell command from the autopilot allowlist."""
    command = _command_for_step(step)
    if command is None:
        return StepResult(False, step, error=f"step is not in autopilot allowlist: {step}", returncode=126)

    completed = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    return StepResult(
        ok=completed.returncode == 0,
        step=step,
        output=completed.stdout,
        error=completed.stderr,
        returncode=completed.returncode,
    )
