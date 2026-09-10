"""Failure-learning ledger and verification policy for PROJECT-BOB.

The ledger turns operational failures into durable prevention rules. It is
intentionally deterministic and local: no network, model, or paid service is
required. The ledger records a failure class, root cause, lesson, prevention,
and regression evidence. Repeated failure classes escalate instead of being
silently retried forever.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class FailureLesson:
    failure_class: str
    root_cause: str
    lesson: str
    prevention: str
    regression: str

    def validate(self) -> None:
        for field in asdict(self).values():
            if not isinstance(field, str) or not field.strip():
                raise ValueError("failure lessons require non-empty text fields")


class LearningLedger:
    """Persist failure lessons and enforce repeat-failure escalation."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def record(self, lesson: FailureLesson) -> None:
        lesson.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        records = list(self._read())
        records.append(asdict(lesson))
        self._atomic_write(records)

    def lessons_for(self, failure_class: str) -> list[FailureLesson]:
        return [
            FailureLesson(**item)
            for item in self._read()
            if item.get("failure_class") == failure_class
        ]

    def known(self, failure_class: str) -> bool:
        return bool(self.lessons_for(failure_class))

    def should_escalate(self, failure_class: str) -> bool:
        """Known failure classes must not silently repeat without escalation."""
        return self.known(failure_class)

    def _read(self) -> Iterable[dict[str, str]]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"learning ledger unreadable: {self.path}") from exc
        if not isinstance(payload, list):
            raise RuntimeError("learning ledger must contain a JSON list")
        return payload

    def _atomic_write(self, records: list[dict[str, str]]) -> None:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            dir=str(self.path.parent),
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(records, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
            raise
