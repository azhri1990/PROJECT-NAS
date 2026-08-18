"""Local, auditable second-brain layer built on verified learning."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from runtime.autonomous_learning import AutonomousLearningLoop, LearnedMemory
from runtime.verified_learning import LearningDecision, LearningType


@dataclass(frozen=True)
class BrainMemory(LearnedMemory):
    source: str
    context: str
    observed_at: str
    verification_status: str
    promotion_reason: str


class SecondBrain:
    """Personal cognitive memory: verified knowledge plus auditable provenance."""

    def __init__(self, db_path: Path | str = Path("runtime/claude-mem-db/second_brain.sqlite3")) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.learning = AutonomousLearningLoop(self.db_path)
        self._init_provenance()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_provenance(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS learning_provenance (
                    id INTEGER PRIMARY KEY,
                    memory_id INTEGER,
                    source TEXT NOT NULL,
                    context TEXT NOT NULL DEFAULT '',
                    observed_at TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    promotion_reason TEXT NOT NULL
                )"""
            )

    def learn(
        self,
        *,
        kind: LearningType,
        statement: str,
        confidence: float,
        evidence: int,
        verified: bool,
        source: str,
        context: str = "",
        contradiction: bool = False,
    ) -> LearningDecision:
        if not source.strip():
            raise ValueError("learning source must not be empty")

        decision = self.learning.learn(
            kind=kind,
            statement=statement,
            confidence=confidence,
            evidence=evidence,
            verified=verified,
            contradiction=contradiction,
        )

        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM learned_memory WHERE statement = ?",
                (statement.strip(),),
            ).fetchone()
            memory_id = row["id"] if row else None
            conn.execute(
                """INSERT INTO learning_provenance
                   (memory_id, source, context, observed_at, verification_status, promotion_reason)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    memory_id,
                    source.strip(),
                    context.strip(),
                    datetime.now(timezone.utc).isoformat(),
                    "verified" if verified else "unverified",
                    decision.reason,
                ),
            )
            if not decision.promoted and memory_id is not None:
                # Never mutate an existing trusted memory merely because a new candidate failed.
                pass
        return decision

    def recall(self, query: str, limit: int = 5) -> list[BrainMemory]:
        memories = self.learning.recall(query, limit)
        if not memories:
            return []

        with self._connect() as conn:
            result: list[BrainMemory] = []
            for memory in memories:
                row = conn.execute(
                    """SELECT source, context, observed_at, verification_status, promotion_reason
                       FROM learning_provenance
                       WHERE memory_id = ? AND verification_status = 'verified'
                       ORDER BY id DESC LIMIT 1""",
                    (memory.id,),
                ).fetchone()
                if not row:
                    continue
                result.append(
                    BrainMemory(
                        id=memory.id,
                        kind=memory.kind,
                        statement=memory.statement,
                        confidence=memory.confidence,
                        evidence=memory.evidence,
                        source=row["source"],
                        context=row["context"],
                        observed_at=row["observed_at"],
                        verification_status=row["verification_status"],
                        promotion_reason=row["promotion_reason"],
                    )
                )
            return result
