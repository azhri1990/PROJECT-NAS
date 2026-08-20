"""Allowlisted local execution primitives for constrained PROJECT-BOB autopilot."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StepResult:
    ok: bool
    step: str
    output: str = ""
    error: str = ""
    returncode: int = 0


def _python_executable(cwd: Path) -> str:
    """Prefer the repository virtualenv so BOB uses its project dependencies."""
    if os.name == "nt":
        candidate = cwd / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = cwd / ".venv" / "bin" / "python"
    return str(candidate) if candidate.exists() else "python"


def _command_for_step(step: str, cwd: Path) -> list[str] | None:
    python = _python_executable(cwd)
    commands: dict[str, list[str]] = {
        "pytest": [python, "-m", "pytest", "-q"],
        "compile": [python, "-m", "compileall", "-q", "runtime", "tests"],
        "diff-check": ["git", "diff", "--check"],
    }
    return commands.get(step)


def run_step(step: str, *, cwd: Path | str = ".") -> StepResult:
    """Execute one fixed, non-shell command from the autopilot allowlist."""
    root = Path(cwd).resolve()
    command = _command_for_step(step, root)
    if command is None:
        return StepResult(False, step, error=f"step is not in autopilot allowlist: {step}", returncode=126)

    completed = subprocess.run(
        command,
        cwd=str(root),
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
