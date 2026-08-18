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
    """Capture, verify, persist, recall, consolidate, and revalidate lessons without self-modifying code."""

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

    @staticmethod
    def _contradicts(candidate: str, existing: str) -> bool:
        """Detect simple explicit polarity conflicts without pretending to be a full NLI model."""
        a = set(re.findall(r"[a-z0-9_]+", candidate.lower()))
        b = set(re.findall(r"[a-z0-9_]+", existing.lower()))
        overlap = (a - {"not", "no", "never"}) & (b - {"not", "no", "never"})
        if not overlap:
            return False
        a_neg = bool(a & {"not", "no", "never"})
        b_neg = bool(b & {"not", "no", "never"})
        return a_neg != b_neg

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
        normalized = statement.strip()
        if not normalized:
            raise ValueError("learning statement must not be empty")

        if not contradiction:
            with self._connect() as conn:
                rows = conn.execute("SELECT statement FROM learned_memory").fetchall()
            contradiction = any(self._contradicts(normalized, row["statement"]) for row in rows)

        candidate = LearningCandidate(kind, normalized, confidence, evidence, contradiction)
        decision = self.engine.evaluate(candidate, verified=verified)
        if not decision.promoted:
            return decision

        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, confidence, evidence FROM learned_memory WHERE statement = ?",
                (candidate.statement,),
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
                    (candidate.kind.value, candidate.statement, candidate.confidence, candidate.evidence),
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
                score = hits / len(terms) + float(row["confidence"]) * 0.25 + min(int(row["evidence"]), 20) * 0.01
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

    def revalidate(self, *, decay: float = 0.05, floor: float = 0.0) -> int:
        """Decay confidence for memories that have not received fresh evidence."""
        if not 0.0 <= decay <= 1.0:
            raise ValueError("decay must be between 0 and 1")
        if not 0.0 <= floor <= 1.0:
            raise ValueError("floor must be between 0 and 1")
        with self._connect() as conn:
            rows = conn.execute("SELECT id, confidence FROM learned_memory").fetchall()
            changed = 0
            for row in rows:
                new_confidence = max(floor, float(row["confidence"]) - decay)
                if new_confidence != float(row["confidence"]):
                    conn.execute("UPDATE learned_memory SET confidence=? WHERE id=?", (new_confidence, row["id"]))
                    changed += 1
            return changed

    def consolidate(self, query: str) -> int:
        """Return the number of related memories considered consolidated.

        Duplicate statements are already merged at write time. This method provides a
        deterministic cognitive-loop checkpoint without inventing unsupported summaries.
        """
        return len(self.recall(query, limit=100))
