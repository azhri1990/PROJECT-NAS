"""Bounded, read-only Git repository inspection."""

import subprocess


MAX_COMMITS = 50


def _git_output(args: list[str]) -> str | None:
    """Run a fixed Git command and return stripped output."""
    try:
        return subprocess.check_output(
            ["git", *args],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def git_branch() -> str | None:
    return _git_output(["rev-parse", "--abbrev-ref", "HEAD"])


def git_status() -> str | None:
    return _git_output(["status", "--porcelain", "--branch"])


def git_recent_commits(commits: int = 10) -> list[str]:
    if not isinstance(commits, int) or isinstance(commits, bool):
        raise ValueError("commits must be an integer")
    if not 0 <= commits <= MAX_COMMITS:
        raise ValueError(f"commits must be between 0 and {MAX_COMMITS}")
    if commits == 0:
        return []

    output = _git_output(["log", "--oneline", "-n", str(commits)])
    return output.splitlines() if output else []


def get_repo_info(commits: int = 10) -> dict:
    return {
        "branch": git_branch() or "unknown",
        "status_porcelain": git_status() or "",
        "recent_commits": git_recent_commits(commits),
    }
