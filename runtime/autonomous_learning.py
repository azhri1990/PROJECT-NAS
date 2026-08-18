"""Zero-cost autonomous learning loop with verified SQLite persistence."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from runtime.verified_learning import LearningCandidate, LearningType, VerifiedLearningEngine, LearningDecision


@dataclass(frozen=True)
class LearnedMemory:
    id: int
    kind: LearningType
    statement: str
    confidence: float
    evidence: int


class AutonomousLearningLoop:
    """Capture, verify, persist, and recall lessons without self-modifying code."""

    def __init__(self, db_path: Path | str = Path("runtime/claude-mem-db/learning.sqlite3")) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = VerifiedLearningEngine()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS learned_memory (
                    id INTEGER PRIMARY KEY,
                    kind TEXT NOT NULL,
                    statement TEXT NOT NULL UNIQUE,
                    confidence REAL NOT NULL,
                    evidence INTEGER NOT NULL
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
        contradiction: bool = False,
    ) -> LearningDecision:
        candidate = LearningCandidate(kind, statement, confidence, evidence, contradiction)
        decision = self.engine.evaluate(candidate, verified=verified)
        if not decision.promoted:
            return decision

        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, confidence, evidence FROM learned_memory WHERE statement = ?",
                (candidate.statement.strip(),),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE learned_memory SET kind=?, confidence=?, evidence=? WHERE id=?",
                    (
                        candidate.kind.value,
                        max(float(row["confidence"]), candidate.confidence),
                        int(row["evidence"]) + candidate.evidence,
                        row["id"],
                    ),
                )
            else:
                conn.execute(
                    "INSERT INTO learned_memory(kind, statement, confidence, evidence) VALUES (?, ?, ?, ?)",
                    (candidate.kind.value, candidate.statement.strip(), candidate.confidence, candidate.evidence),
                )
        return decision

    def recall(self, query: str, limit: int = 5) -> list[LearnedMemory]:
        terms = re.findall(r"[a-z0-9_]+", query.lower())
        if not terms or limit < 1:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, kind, statement, confidence, evidence FROM learned_memory"
            ).fetchall()
        scored: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            text = row["statement"].lower()
            hits = sum(1 for term in terms if term in text)
            if hits:
                score = hits / len(terms) + float(row["confidence"]) * 0.25
                scored.append((score, row))
        scored.sort(key=lambda item: (item[0], item[1]["confidence"], item[1]["evidence"]), reverse=True)
        return [
            LearnedMemory(
                id=row["id"],
                kind=LearningType(row["kind"]),
                statement=row["statement"],
                confidence=row["confidence"],
                evidence=row["evidence"],
            )
            for _, row in scored[:limit]
        ]
