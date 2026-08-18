"""Zero-cost, inspectable cognitive memory lifecycle for PROJECT-NAS."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class MemoryLifecycle(str, Enum):
    NEW = "NEW"
    VERIFIED = "VERIFIED"
    TRUSTED = "TRUSTED"
    PINNED = "PINNED"
    STALE = "STALE"
    CONFLICTED = "CONFLICTED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class MemoryProvenance:
    source: str
    reference: str

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("provenance source must not be empty")
        if not self.reference.strip():
            raise ValueError("provenance reference must not be empty")


@dataclass(frozen=True)
class CognitiveMemory:
    id: str
    kind: str
    statement: str
    lifecycle: MemoryLifecycle
    confidence: float
    evidence: int
    created_at: str
    updated_at: str
    provenance: MemoryProvenance


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _memory_id(statement: str, kind: str) -> str:
    normalized = " ".join(statement.lower().split())
    return hashlib.sha256(f"{kind}:{normalized}".encode("utf-8")).hexdigest()[:24]


def _tokens(statement: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", statement.lower()))


def _contradicts(candidate: str, existing: str) -> bool:
    """Detect simple explicit polarity conflicts without pretending to be NLI."""
    a = _tokens(candidate)
    b = _tokens(existing)
    negation = {"not", "no", "never"}
    overlap = (a - negation) & (b - negation)
    if not overlap:
        return False
    return bool(a & negation) != bool(b & negation)


class CognitiveMemoryStore:
    """Persistent cognitive memory with explicit lifecycle, provenance and rollback."""

    def __init__(self, db_path: Path | str = Path("runtime/claude-mem-db/cognitive_memory.sqlite3")) -> None:
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
                """CREATE TABLE IF NOT EXISTS cognitive_memory (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    lifecycle TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    evidence INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    reference TEXT NOT NULL
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS cognitive_memory_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    lifecycle TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    evidence INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    reference TEXT NOT NULL,
                    approver TEXT NOT NULL DEFAULT '',
                    changed_at TEXT NOT NULL
                )"""
            )

    @staticmethod
    def _validate_confidence(value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return float(value)

    @staticmethod
    def _validate_evidence(value: int) -> int:
        if value < 0:
            raise ValueError("evidence must not be negative")
        return int(value)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> CognitiveMemory:
        return CognitiveMemory(
            id=row["id"],
            kind=row["kind"],
            statement=row["statement"],
            lifecycle=MemoryLifecycle(row["lifecycle"]),
            confidence=float(row["confidence"]),
            evidence=int(row["evidence"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            provenance=MemoryProvenance(row["source"], row["reference"]),
        )

    @staticmethod
    def _snapshot(conn: sqlite3.Connection, memory: CognitiveMemory, action: str, approver: str = "") -> None:
        conn.execute(
            """INSERT INTO cognitive_memory_history
               (memory_id, action, lifecycle, confidence, evidence, source, reference, approver, changed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                memory.id,
                action,
                memory.lifecycle.value,
                memory.confidence,
                memory.evidence,
                memory.provenance.source,
                memory.provenance.reference,
                approver,
                _now(),
            ),
        )

    def _get(self, memory_id: str) -> CognitiveMemory:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM cognitive_memory WHERE id=?", (memory_id,)).fetchone()
        if row is None:
            raise KeyError(f"memory not found: {memory_id}")
        return self._from_row(row)

    def add(
        self,
        statement: str,
        kind: str,
        provenance: MemoryProvenance,
        *,
        confidence: float = 0.0,
        evidence: int = 0,
    ) -> CognitiveMemory:
        statement = statement.strip()
        kind = kind.strip().upper()
        if not statement:
            raise ValueError("memory statement must not be empty")
        if not kind:
            raise ValueError("memory kind must not be empty")
        confidence = self._validate_confidence(confidence)
        evidence = self._validate_evidence(evidence)
        now = _now()
        memory_id = _memory_id(statement, kind)
        with self._connect() as conn:
            existing = conn.execute("SELECT * FROM cognitive_memory WHERE id=?", (memory_id,)).fetchone()
            if existing is None:
                conn.execute(
                    """INSERT INTO cognitive_memory
                       (id, kind, statement, lifecycle, confidence, evidence, created_at, updated_at, source, reference)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (memory_id, kind, statement, MemoryLifecycle.NEW.value, confidence, evidence, now, now, provenance.source, provenance.reference),
                )
            else:
                current = self._from_row(existing)
                self._snapshot(conn, current, "CONSOLIDATE")
                conn.execute(
                    """UPDATE cognitive_memory
                       SET confidence=MAX(confidence, ?), evidence=evidence+?, updated_at=?, source=?, reference=?
                       WHERE id=?""",
                    (confidence, evidence, now, provenance.source, provenance.reference, memory_id),
                )
        return self._get(memory_id)

    def consolidate(
        self,
        statement: str,
        kind: str,
        provenance: MemoryProvenance,
        *,
        confidence: float = 0.0,
        evidence: int = 1,
    ) -> CognitiveMemory:
        """Merge one observed instance into existing identical knowledge."""
        if evidence < 1:
            raise ValueError("consolidation evidence must be at least 1")
        return self.add(statement, kind, provenance, confidence=confidence, evidence=evidence)

    def promote_verified(self, memory_id: str, *, confidence: float, evidence: int) -> CognitiveMemory:
        confidence = self._validate_confidence(confidence)
        evidence = self._validate_evidence(evidence)
        memory = self._get(memory_id)
        if memory.kind == "POLICY":
            return memory
        lifecycle = MemoryLifecycle.TRUSTED if confidence >= 0.75 and evidence >= 2 else MemoryLifecycle.VERIFIED
        with self._connect() as conn:
            self._snapshot(conn, memory, "PROMOTE_VERIFIED")
            conn.execute(
                "UPDATE cognitive_memory SET lifecycle=?, confidence=?, evidence=?, updated_at=? WHERE id=?",
                (lifecycle.value, confidence, evidence, _now(), memory_id),
            )
        return self._get(memory_id)

    def approve_pinned(self, memory_id: str, *, approver: str = "user") -> CognitiveMemory:
        approver = approver.strip()
        if not approver:
            raise ValueError("approver must not be empty")
        memory = self._get(memory_id)
        if memory.kind == "POLICY":
            raise PermissionError("policy knowledge cannot be pinned automatically")
        if memory.lifecycle == MemoryLifecycle.PINNED:
            return memory
        with self._connect() as conn:
            self._snapshot(conn, memory, "PIN", approver)
            conn.execute(
                "UPDATE cognitive_memory SET lifecycle=?, updated_at=? WHERE id=?",
                (MemoryLifecycle.PINNED.value, _now(), memory_id),
            )
        return self._get(memory_id)

    def history(self, memory_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT id, memory_id, action, lifecycle, confidence, evidence, source, reference, approver, changed_at
                   FROM cognitive_memory_history WHERE memory_id=? ORDER BY id""",
                (memory_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def rollback(self, memory_id: str) -> CognitiveMemory:
        memory = self._get(memory_id)
        with self._connect() as conn:
            row = conn.execute(
                """SELECT * FROM cognitive_memory_history WHERE memory_id=? ORDER BY id DESC LIMIT 1""",
                (memory_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"no rollback history for memory: {memory_id}")
            conn.execute(
                """UPDATE cognitive_memory
                   SET lifecycle=?, confidence=?, evidence=?, source=?, reference=?, updated_at=?
                   WHERE id=?""",
                (
                    row["lifecycle"],
                    row["confidence"],
                    row["evidence"],
                    row["source"],
                    row["reference"],
                    _now(),
                    memory_id,
                ),
            )
            conn.execute("DELETE FROM cognitive_memory_history WHERE id=?", (row["id"],))
        return self._get(memory_id)

    def find_contradictions(self, statement: str, kind: str | None = None, limit: int = 20) -> list[CognitiveMemory]:
        statement = statement.strip()
        if not statement:
            raise ValueError("statement must not be empty")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
            raise ValueError("limit must be an integer from 1 to 20")
        normalized_kind = kind.strip().upper() if kind else None
        query = "SELECT * FROM cognitive_memory WHERE lifecycle NOT IN (?, ?)"
        params: list[Any] = [MemoryLifecycle.REJECTED.value, MemoryLifecycle.CONFLICTED.value]
        if normalized_kind:
            query += " AND kind=?"
            params.append(normalized_kind)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        matches = [self._from_row(row) for row in rows if _contradicts(statement, row["statement"])]
        return matches[:limit]

    def mark_conflicted(self, memory_id: str, provenance: MemoryProvenance) -> CognitiveMemory:
        memory = self._get(memory_id)
        with self._connect() as conn:
            self._snapshot(conn, memory, "CONFLICT")
            conn.execute(
                "UPDATE cognitive_memory SET lifecycle=?, updated_at=?, source=?, reference=? WHERE id=?",
                (MemoryLifecycle.CONFLICTED.value, _now(), provenance.source, provenance.reference, memory_id),
            )
        return self._get(memory.id)

    def record_evidence(self, memory_id: str, amount: int = 1) -> CognitiveMemory:
        if amount < 1:
            raise ValueError("evidence amount must be at least 1")
        memory = self._get(memory_id)
        new_evidence = memory.evidence + amount
        lifecycle = MemoryLifecycle.TRUSTED if memory.lifecycle == MemoryLifecycle.VERIFIED and memory.confidence >= 0.75 and new_evidence >= 2 else memory.lifecycle
        with self._connect() as conn:
            self._snapshot(conn, memory, "EVIDENCE")
            conn.execute(
                "UPDATE cognitive_memory SET evidence=?, lifecycle=?, updated_at=? WHERE id=?",
                (new_evidence, lifecycle.value, _now(), memory_id),
            )
        return self._get(memory_id)

    def revalidate(self, *, decay: float = 0.05, floor: float = 0.0) -> int:
        if not 0.0 <= decay <= 1.0:
            raise ValueError("decay must be between 0 and 1")
        if not 0.0 <= floor <= 1.0:
            raise ValueError("floor must be between 0 and 1")
        changed = 0
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM cognitive_memory").fetchall()
            for row in rows:
                if row["lifecycle"] in {MemoryLifecycle.REJECTED.value, MemoryLifecycle.CONFLICTED.value, MemoryLifecycle.PINNED.value}:
                    continue
                new_confidence = max(floor, float(row["confidence"]) - decay)
                lifecycle = row["lifecycle"]
                if new_confidence < 0.5 and lifecycle == MemoryLifecycle.TRUSTED.value:
                    lifecycle = MemoryLifecycle.STALE.value
                if new_confidence != float(row["confidence"]) or lifecycle != row["lifecycle"]:
                    self._snapshot(conn, self._from_row(row), "REVALIDATE")
                    conn.execute("UPDATE cognitive_memory SET confidence=?, lifecycle=?, updated_at=? WHERE id=?", (new_confidence, lifecycle, _now(), row["id"]))
                    changed += 1
        return changed

    def review(self, *, decay: float = 0.05, floor: float = 0.0) -> dict[str, int]:
        """Run bounded local maintenance and return lifecycle counts."""
        self.revalidate(decay=decay, floor=floor)
        with self._connect() as conn:
            rows = conn.execute("SELECT lifecycle, COUNT(*) AS count FROM cognitive_memory GROUP BY lifecycle").fetchall()
        counts = {lifecycle.value: 0 for lifecycle in MemoryLifecycle}
        counts.update({row["lifecycle"]: int(row["count"]) for row in rows})
        return counts

    def recall(self, query: str, limit: int = 5) -> list[CognitiveMemory]:
        if not isinstance(query, str) or not query.strip():
            return []
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            return []
        limit = min(limit, 20)
        terms = _tokens(query)
        if not terms:
            return []
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM cognitive_memory WHERE lifecycle != ?", (MemoryLifecycle.REJECTED.value,)).fetchall()
        ranked: list[tuple[float, CognitiveMemory]] = []
        for row in rows:
            memory = self._from_row(row)
            tokens = _tokens(memory.statement)
            hits = len(terms & tokens)
            if not hits:
                continue
            lifecycle_bonus = {
                MemoryLifecycle.PINNED: 0.30,
                MemoryLifecycle.TRUSTED: 0.20,
                MemoryLifecycle.VERIFIED: 0.10,
            }.get(memory.lifecycle, 0.0)
            score = hits / len(terms) + memory.confidence * 0.25 + min(memory.evidence, 20) * 0.01 + lifecycle_bonus
            ranked.append((score, memory))
        ranked.sort(key=lambda item: (item[0], item[1].confidence, item[1].evidence, item[1].updated_at), reverse=True)
        return [memory for _, memory in ranked[:limit]]
