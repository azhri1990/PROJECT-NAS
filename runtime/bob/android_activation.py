"""Android/Termux activation primitives for PROJECT-BOB.

This module owns local worker configuration and safe lifecycle requests. It does
not execute arbitrary remote commands and never stores credentials in source.
"""
from __future__ import annotations

import json
import os
import secrets
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_STATE_DIR = Path.home() / ".project-nas" / "bob-worker"


@dataclass(frozen=True)
class WorkerConfig:
    worker_id: str
    endpoint: str
    token: str
    platform: str = "android"
    capabilities: tuple[str, ...] = ("read_repository", "read_runtime")

    def __post_init__(self) -> None:
        if not self.worker_id.strip():
            raise ValueError("worker_id must not be empty")
        if not self.endpoint.startswith(("http://", "https://")):
            raise ValueError("endpoint must use http:// or https://")
        if not self.token.strip():
            raise ValueError("token must not be empty")
        if self.platform != "android":
            raise ValueError("Android activation requires platform=android")

    def as_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "endpoint": self.endpoint.rstrip("/"),
            "token": self.token,
            "platform": self.platform,
            "capabilities": list(self.capabilities),
        }


def generate_worker_id(prefix: str = "android") -> str:
    return f"{prefix}-{secrets.token_hex(8)}"


def config_path(state_dir: Path = DEFAULT_STATE_DIR) -> Path:
    return state_dir / "config.json"


def write_config(config: WorkerConfig, state_dir: Path = DEFAULT_STATE_DIR) -> Path:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = config_path(state_dir)
    fd, tmp_name = tempfile.mkstemp(prefix="config-", suffix=".tmp", dir=state_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(config.as_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return path


def read_config(state_dir: Path = DEFAULT_STATE_DIR) -> WorkerConfig:
    path = config_path(state_dir)
    data = json.loads(path.read_text(encoding="utf-8"))
    return WorkerConfig(
        worker_id=str(data["worker_id"]),
        endpoint=str(data["endpoint"]),
        token=str(data["token"]),
        platform=str(data.get("platform", "android")),
        capabilities=tuple(str(x) for x in data.get("capabilities", [])),
    )


def doctor(state_dir: Path = DEFAULT_STATE_DIR) -> dict[str, Any]:
    checks: dict[str, bool] = {
        "state_dir": state_dir.exists() and state_dir.is_dir(),
        "config": config_path(state_dir).is_file(),
    }
    config: WorkerConfig | None = None
    if checks["config"]:
        try:
            config = read_config(state_dir)
            checks["config_valid"] = True
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            checks["config_valid"] = False
    else:
        checks["config_valid"] = False
    if config is not None:
        checks["endpoint_valid"] = config.endpoint.startswith(("http://", "https://"))
        checks["token_present"] = bool(config.token)
    else:
        checks["endpoint_valid"] = False
        checks["token_present"] = False
    return {"ok": all(checks.values()), "checks": checks}
