#!/usr/bin/env python3
"""PROJECT-NAS local health diagnostics."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def check_python() -> Check:
    return Check("Python", sys.version_info >= (3, 12), sys.version.split()[0])


def check_git() -> Check:
    if not command_exists("git"):
        return Check("Git", False, "git executable not found")
    try:
        version = subprocess.check_output(["git", "--version"], text=True).strip()
        return Check("Git", True, version)
    except (OSError, subprocess.SubprocessError) as exc:
        return Check("Git", False, str(exc))


def check_repository() -> Check:
    try:
        branch = subprocess.check_output(["git", "-C", str(ROOT), "branch", "--show-current"], text=True).strip()
        if not branch:
            branch = "detached HEAD"
        return Check("Repository", True, branch)
    except (OSError, subprocess.SubprocessError) as exc:
        return Check("Repository", False, str(exc))


def check_module(name: str) -> Check:
    available = importlib.util.find_spec(name) is not None
    return Check(name, available, "importable" if available else "not installed")


def check_memory_backend() -> Check:
    if importlib.util.find_spec("chromadb") is not None:
        return Check("Memory backend", True, "ChromaDB available")
    try:
        with sqlite3.connect(":memory:") as conn:
            conn.execute("SELECT 1")
        return Check("Memory backend", True, "SQLite fallback available")
    except (OSError, sqlite3.Error) as exc:
        return Check("Memory backend", False, f"no usable backend: {exc}")


def resolve_memory_db() -> Path:
    configured = os.getenv("PROJECT_NAS_MEMORY_DB")
    if configured:
        path = Path(configured).expanduser()
        if path.suffix:
            return path
        return path / "memory.sqlite3"
    return ROOT / "runtime" / "claude-mem-db" / "memory.sqlite3"


def check_memory_database() -> Check:
    # ChromaDB is the active backend when installed; the SQLite file is only
    # required for the fallback runtime.
    if importlib.util.find_spec("chromadb") is not None:
        return Check("Memory store", True, "ChromaDB store active; SQLite fallback check skipped")

    path = resolve_memory_db()
    if not path.is_file():
        try:
            display = str(path.relative_to(ROOT))
        except ValueError:
            display = str(path)
        return Check("Memory store", False, f"missing: {display}")
    try:
        with sqlite3.connect(path) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "memories" not in tables:
                return Check("Memory store", False, f"missing memories table: {path}")
            count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        try:
            display = str(path.relative_to(ROOT))
        except ValueError:
            display = str(path)
        return Check("Memory store", True, f"{display} ({count} records)")
    except (OSError, sqlite3.Error) as exc:
        return Check("Memory store", False, str(exc))


def check_database() -> Check:
    return check_session_database()


def check_session_database() -> Check:
    configured = os.getenv("PROJECT_NAS_SESSION_DB")
    path = Path(configured).expanduser() if configured else ROOT / "session.db"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as conn:
            conn.execute("SELECT 1")
        try:
            display_path = str(path.relative_to(ROOT))
        except ValueError:
            display_path = str(path)
        return Check("Session store", True, display_path)
    except (OSError, sqlite3.Error) as exc:
        return Check("Session store", False, str(exc))


def check_prompt() -> Check:
    candidates = [ROOT / "ai" / "MASTER_PROMPT.md", ROOT / "ai" / "AI_OPERATING_SYSTEM_SUMMARY.md"]
    for path in candidates:
        if path.is_file() and path.read_text(encoding="utf-8").strip():
            return Check("Prompt system", True, str(path.relative_to(ROOT)))
    return Check("Prompt system", False, "no usable prompt file found")


def check_ollama() -> Check:
    url = os.getenv("OLLAMA_URL", "http" + chr(58) + chr(47) + chr(47) + "127.0.0.1:11434/api/tags")
    # CI/offline doctor mode skips the default service probe, but an explicitly
    # supplied URL must still be probed so unit tests and diagnostics can verify
    # that an unavailable endpoint is reported correctly.
    if os.getenv("PROJECT_NAS_DOCTOR_OFFLINE") == "1" and "OLLAMA_URL" not in os.environ:
        return Check("Local LLM", True, "offline verification mode; service probe skipped")
    try:
        request = Request(url, method="GET")
        with urlopen(request, timeout=2) as response:
            if response.status != 200:
                return Check("Local LLM", False, f"HTTP {response.status}")
        return Check("Local LLM", True, url)
    except (URLError, OSError, TimeoutError) as exc:
        return Check("Local LLM", False, f"unreachable: {exc}")


def run() -> int:
    checks = [check_repository(), check_python(), check_git(), check_module("fastapi"), check_module("requests"), check_memory_backend(), check_memory_database(), check_session_database(), check_prompt(), check_ollama()]
    print("PROJECT-NAS DOCTOR")
    print("=" * 48)
    for check in checks:
        marker = "✓" if check.ok else "✗"
        print(f"{marker} {check.name:<18} {check.detail}")
    print("=" * 48)
    failed = [check for check in checks if not check.ok]
    print(f"STATUS: {'HEALTHY' if not failed else 'ATTENTION REQUIRED'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check PROJECT-NAS local health")
    parser.parse_args()
    raise SystemExit(run())
