"""Bounded, local-only certification history for PROJECT-NAS."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CertificationHistory:
    """Append-only JSONL history with a hard byte bound."""

    def __init__(self, path: str | Path, max_bytes: int = 65_536) -> None:
        self.path = Path(path)
        self.max_bytes = max(256, int(max_bytes))

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                records.append(value)
        return records

    def latest(self) -> dict[str, Any] | None:
        records = self.records()
        return records[-1] if records else None

    def record(
        self,
        *,
        timestamp: str,
        commit: str,
        result: str,
        tests: int,
        gates: dict[str, str],
    ) -> None:
        if result not in {"GREEN", "RED"}:
            raise ValueError("result must be GREEN or RED")
        if tests < 0:
            raise ValueError("tests must be non-negative")
        if not isinstance(gates, dict):
            raise ValueError("gates must be an object")

        record = {
            "timestamp": timestamp,
            "commit": commit,
            "result": result,
            "tests": tests,
            "gates": gates,
        }
        encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        if len(encoded) > self.max_bytes:
            raise ValueError("certification record exceeds history byte bound")

        records = self.records()
        records.append(record)
        lines = [json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in records]

        while len("".join(lines).encode("utf-8")) > self.max_bytes and len(lines) > 1:
            lines.pop(0)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("".join(lines), encoding="utf-8")
