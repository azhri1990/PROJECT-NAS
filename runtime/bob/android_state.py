"""Small crash-safe state store for the Android/Termux BOB worker."""
from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


class AndroidState:
    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"pending_results": {}}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("pending_results", {}), dict):
            raise ValueError("invalid worker state")
        return data

    def save(self, data: dict[str, Any]) -> None:
        safe = {"pending_results": dict(data.get("pending_results", {}))}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, delete=False) as handle:
            json.dump(safe, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = handle.name
        os.replace(temporary, self.path)

    def queue_result(self, lease_id: str, payload: dict[str, Any]) -> None:
        data = self.load()
        data["pending_results"][lease_id] = dict(payload)
        self.save(data)

    def remove_result(self, lease_id: str) -> None:
        data = self.load()
        data["pending_results"].pop(lease_id, None)
        self.save(data)
