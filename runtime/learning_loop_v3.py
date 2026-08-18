"""Bounded, auditable local learning loop for JARVIS/PROJECT-NAS."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.adaptive_decision import OutcomeStatus
from runtime.verified_learning import LearningType


@dataclass(frozen=True)
class LearningObservation:
    id: str
    task: str
    strategy_id: str
    context: str
    source: str
    created_at: str


@dataclass(frozen=True)
class LearningOutcome:
    observation_id: str
    status: OutcomeStatus
    evidence: int
    learned: bool
    lesson: str | None


class LearningLoopV3:
    """Observe -> evaluate -> consolidate -> adapt -> measure, without self-modifying authority."""

    MAX_TEXT = 1024
    MAX_CONTEXT = 2048
    MAX_SOURCE = 256
    MAX_LESSON = 2048

    def __init__(self, brain: Any, db_path: Path | str = Path("runtime/claude-mem-db/learning_loop_v3.sqlite3")) -> None:
        self.brain = brain
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS observations (
                    id TEXT PRIMARY KEY,
                    task TEXT NOT NULL,
                    strategy_id TEXT NOT NULL,
                    context TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observation_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    evidence INTEGER NOT NULL,
                    lesson TEXT,
                    learned INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )

    @classmethod
    def _text(cls, value: str, field: str, maximum: int) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{field} must be a string")
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field} must not be empty")
        if len(normalized) > maximum:
            raise ValueError(f"{field} exceeds maximum length of {maximum}")
        return normalized

    def observe(self, task: str, strategy_id: str, context: str, source: str) -> str:
        task = self._text(task, "task", self.MAX_TEXT)
        strategy_id = self._text(strategy_id, "strategy_id", 128)
        context = self._text(context, "context", self.MAX_CONTEXT)
        source = self._text(source, "source", self.MAX_SOURCE)
        observation_id = uuid.uuid4().hex[:24]
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO observations(id, task, strategy_id, context, source, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (observation_id, task, strategy_id, context, source, datetime.now(timezone.utc).isoformat()),
            )
        return observation_id

    def _observation(self, observation_id: str) -> LearningObservation:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM observations WHERE id=?", (observation_id,)).fetchone()
        if row is None:
            raise KeyError(f"observation not found: {observation_id}")
        return LearningObservation(row["id"], row["task"], row["strategy_id"], row["context"], row["source"], row["created_at"])

    def record_outcome(
        self,
        observation_id: str,
        status: OutcomeStatus,
        *,
        evidence: int = 1,
        lesson: str | None = None,
    ) -> LearningOutcome:
        observation = self._observation(observation_id)
        if not isinstance(status, OutcomeStatus):
            raise ValueError("status must be an OutcomeStatus")
        if isinstance(evidence, bool) or not isinstance(evidence, int) or evidence < 0 or evidence > 100:
            raise ValueError("evidence must be an integer from 0 to 100")
        if lesson is not None:
            lesson = self._text(lesson, "lesson", self.MAX_LESSON)

        with self._connect() as conn:
            existing = conn.execute("SELECT 1 FROM outcomes WHERE observation_id=?", (observation_id,)).fetchone()
            if existing:
                raise ValueError(f"outcome already recorded: {observation_id}")

        learned = False
        if status is not OutcomeStatus.UNKNOWN:
            self.brain.record_outcome(observation.strategy_id, status)
            if lesson and status in {OutcomeStatus.SUCCESS, OutcomeStatus.PARTIAL} and evidence >= 2:
                decision = self.brain.learn(
                    kind=LearningType.DECISION,
                    statement=lesson,
                    confidence=0.75 if status is OutcomeStatus.SUCCESS else 0.65,
                    evidence=evidence,
                    verified=True,
                    source=observation.source,
                    context=observation.context,
                )
                learned = decision.promoted

        with self._connect() as conn:
            conn.execute(
                "INSERT INTO outcomes(observation_id, status, evidence, lesson, learned, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (observation_id, status.value, evidence, lesson, int(learned), datetime.now(timezone.utc).isoformat()),
            )
        return LearningOutcome(observation_id, status, evidence, learned, lesson)

    def consolidate(self, query: str, limit: int = 20):
        query = self._text(query, "query", self.MAX_TEXT)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
            raise ValueError("limit must be an integer from 1 to 20")
        return self.brain.recall(query, limit=limit)

    def metrics(self) -> dict[str, float | int]:
        with self._connect() as conn:
            totals = conn.execute(
                """SELECT
                    COUNT(*) AS total,
                    SUM(status='SUCCESS') AS success,
                    SUM(status='PARTIAL') AS partial,
                    SUM(status='FAILURE') AS failure,
                    SUM(status='UNKNOWN') AS unknown,
                    SUM(learned=1) AS learned
                   FROM outcomes"""
            ).fetchone()
        total = int(totals["total"] or 0)
        success = int(totals["success"] or 0)
        partial = int(totals["partial"] or 0)
        failure = int(totals["failure"] or 0)
        unknown = int(totals["unknown"] or 0)
        learned = int(totals["learned"] or 0)
        measured = success + partial + failure
        return {
            "observations": self._count("observations"),
            "outcomes": total,
            "successful_outcomes": success,
            "partial_outcomes": partial,
            "failed_outcomes": failure,
            "unknown_outcomes": unknown,
            "learning_updates": learned,
            "measured_outcomes": measured,
            "success_rate": success / measured if measured else 0.0,
        }

    def _count(self, table: str) -> int:
        if table not in {"observations", "outcomes"}:
            raise ValueError("unsupported metrics table")
        with self._connect() as conn:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0])
