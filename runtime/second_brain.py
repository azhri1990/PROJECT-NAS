"""Local, auditable second-brain layer built on verified learning."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from runtime.autonomous_learning import AutonomousLearningLoop, LearnedMemory
from runtime.cognitive_memory import CognitiveMemory, MemoryLifecycle
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

    MAX_GAP_QUERIES = 20
    MAX_QUERY_CHARS = 256

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

    def _cognitive_memory_for(self, memory_id: int | str) -> CognitiveMemory:
        if isinstance(memory_id, bool):
            raise ValueError("memory_id must be an integer or cognitive memory id")
        if isinstance(memory_id, int):
            with self._connect() as conn:
                row = conn.execute("SELECT statement, kind FROM learned_memory WHERE id=?", (memory_id,)).fetchone()
            if row is None:
                raise KeyError(f"memory not found: {memory_id}")
            matches = self.learning.cognitive_memory.recall(row["statement"], limit=20)
            for memory in matches:
                if memory.statement == row["statement"] and memory.kind == row["kind"]:
                    return memory
            raise KeyError(f"cognitive memory not found: {memory_id}")
        if isinstance(memory_id, str) and memory_id.strip():
            return self.learning.cognitive_memory._get(memory_id.strip())
        raise ValueError("memory_id must be an integer or cognitive memory id")

    def knowledge_gaps(self, queries: list[str]) -> list[str]:
        """Return bounded queries for which the second brain has no recalled knowledge."""
        if not isinstance(queries, list):
            raise ValueError("queries must be a list")
        if len(queries) > self.MAX_GAP_QUERIES:
            raise ValueError(f"queries must contain at most {self.MAX_GAP_QUERIES} items")
        gaps: list[str] = []
        for query in queries:
            if not isinstance(query, str) or not query.strip():
                raise ValueError("knowledge-gap queries must be non-empty strings")
            normalized = query.strip()
            if len(normalized) > self.MAX_QUERY_CHARS:
                raise ValueError(f"knowledge-gap query exceeds {self.MAX_QUERY_CHARS} characters")
            if not self.learning.recall_cognitive(normalized, limit=1):
                gaps.append(normalized)
        return gaps

    def approve_permanent(self, memory_id: int | str, *, approver: str = "user") -> CognitiveMemory:
        """Explicitly promote existing knowledge to the permanent PINNED lifecycle."""
        memory = self._cognitive_memory_for(memory_id)
        if memory.lifecycle not in {MemoryLifecycle.VERIFIED, MemoryLifecycle.TRUSTED, MemoryLifecycle.PINNED}:
            raise PermissionError("only verified or trusted memory can be pinned")
        return self.learning.cognitive_memory.approve_pinned(memory.id, approver=approver)

    def memory_history(self, memory_id: int | str) -> list[dict]:
        memory = self._cognitive_memory_for(memory_id)
        return self.learning.cognitive_memory.history(memory.id)

    def rollback_memory(self, memory_id: int | str) -> CognitiveMemory:
        memory = self._cognitive_memory_for(memory_id)
        return self.learning.cognitive_memory.rollback(memory.id)

    def review_memory(self, *, decay: float = 0.05, floor: float = 0.0) -> dict[str, int]:
        """Run bounded deterministic cognitive-memory maintenance."""
        return self.learning.cognitive_memory.review(decay=decay, floor=floor)
