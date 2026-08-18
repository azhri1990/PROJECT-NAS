"""Zero-cost autonomous learning loop with verified SQLite persistence."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from runtime.cognitive_memory import CognitiveMemory, CognitiveMemoryStore, MemoryProvenance
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

    def __init__(
        self,
        db_path: Path | str = Path("runtime/claude-mem-db/learning.sqlite3"),
        cognitive_db_path: Path | str | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = VerifiedLearningEngine()
        self.cognitive_memory = CognitiveMemoryStore(
            cognitive_db_path or self.db_path.parent / "cognitive_memory.sqlite3"
        )
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

        self.cognitive_memory.add(
            candidate.statement,
            candidate.kind.value,
            MemoryProvenance("autonomous_learning", candidate.statement),
            confidence=candidate.confidence,
            evidence=candidate.evidence,
        )
        cognitive = self.cognitive_memory.recall(candidate.statement, limit=1)
        if cognitive and cognitive[0].lifecycle.value == "NEW":
            self.cognitive_memory.promote_verified(
                cognitive[0].id,
                confidence=candidate.confidence,
                evidence=candidate.evidence,
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

    def recall_cognitive(self, query: str, limit: int = 5):
        """Return lifecycle-aware memories from the cognitive layer."""
        return self.cognitive_memory.recall(query, limit=limit)

    def revalidate(self, *, decay: float = 0.05, floor: float = 0.0) -> int:
        """Decay confidence in both legacy and cognitive memory stores."""
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
        self.cognitive_memory.revalidate(decay=decay, floor=floor)
        return changed

    def consolidate(self, query: str) -> int:
        """Consolidate only evidence already present; never invent summaries."""
        return len(self.cognitive_memory.recall(query, limit=100))

    def review_memory(self, *, decay: float = 0.05, floor: float = 0.0) -> dict[str, int]:
        """Run deterministic cognitive-memory maintenance and return lifecycle counts."""
        return self.cognitive_memory.review(decay=decay, floor=floor)

    def approve_permanent(self, memory: int | str, *, approver: str = "user") -> CognitiveMemory:
        """Explicitly pin only existing verified/trusted knowledge."""
        if isinstance(memory, int) and not isinstance(memory, bool):
            with self._connect() as conn:
                row = conn.execute("SELECT statement FROM learned_memory WHERE id=?", (memory,)).fetchone()
            if row is None:
                raise KeyError(f"memory not found: {memory}")
            matches = self.cognitive_memory.recall(row["statement"], limit=20)
            cognitive = next((item for item in matches if item.statement == row["statement"]), None)
        elif isinstance(memory, str) and memory.strip():
            matches = self.cognitive_memory.recall(memory.strip(), limit=1)
            cognitive = matches[0] if matches and matches[0].statement == memory.strip() else None
        else:
            raise ValueError("memory must be an integer legacy id or exact statement")
        if cognitive is None:
            raise KeyError(f"cognitive memory not found: {memory}")
        if cognitive.lifecycle.value not in {"VERIFIED", "TRUSTED", "PINNED"}:
            raise PermissionError("only verified or trusted memory can be pinned")
        return self.cognitive_memory.approve_pinned(cognitive.id, approver=approver)

    def rollback_memory(self, memory_id: str) -> CognitiveMemory:
        """Rollback the latest cognitive-memory lifecycle change."""
        return self.cognitive_memory.rollback(memory_id)
