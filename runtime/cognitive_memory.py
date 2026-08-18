"""Zero-cost, inspectable cognitive memory lifecycle for PROJECT-NAS."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


class MemoryLifecycle(str, Enum):
    NEW = "NEW"
    VERIFIED = "VERIFIED"
    TRUSTED = "TRUSTED"
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


class CognitiveMemoryStore:
    """Persistent cognitive memory with explicit lifecycle and provenance."""

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
            existing = conn.execute("SELECT id FROM cognitive_memory WHERE id=?", (memory_id,)).fetchone()
            if existing is None:
                conn.execute(
                    """INSERT INTO cognitive_memory
                       (id, kind, statement, lifecycle, confidence, evidence, created_at, updated_at, source, reference)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (memory_id, kind, statement, MemoryLifecycle.NEW.value, confidence, evidence, now, now, provenance.source, provenance.reference),
                )
            else:
                conn.execute(
                    """UPDATE cognitive_memory
                       SET confidence=MAX(confidence, ?), evidence=evidence+?, updated_at=?, source=?, reference=?
                       WHERE id=?""",
                    (confidence, evidence, now, provenance.source, provenance.reference, memory_id),
                )
        return self._get(memory_id)

    def promote_verified(self, memory_id: str, *, confidence: float, evidence: int) -> CognitiveMemory:
        confidence = self._validate_confidence(confidence)
        evidence = self._validate_evidence(evidence)
        memory = self._get(memory_id)
        if memory.kind == "POLICY":
            return memory
        lifecycle = MemoryLifecycle.TRUSTED if confidence >= 0.75 and evidence >= 2 else MemoryLifecycle.VERIFIED
        with self._connect() as conn:
            conn.execute(
                "UPDATE cognitive_memory SET lifecycle=?, confidence=?, evidence=?, updated_at=? WHERE id=?",
                (lifecycle.value, confidence, evidence, _now(), memory_id),
            )
        return self._get(memory_id)

    def mark_conflicted(self, memory_id: str, provenance: MemoryProvenance) -> CognitiveMemory:
        memory = self._get(memory_id)
        with self._connect() as conn:
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
            rows = conn.execute("SELECT id, confidence, lifecycle FROM cognitive_memory").fetchall()
            for row in rows:
                if row["lifecycle"] in {MemoryLifecycle.REJECTED.value, MemoryLifecycle.CONFLICTED.value}:
                    continue
                new_confidence = max(floor, float(row["confidence"]) - decay)
                lifecycle = row["lifecycle"]
                if new_confidence < 0.5 and lifecycle == MemoryLifecycle.TRUSTED.value:
                    lifecycle = MemoryLifecycle.STALE.value
                if new_confidence != float(row["confidence"]) or lifecycle != row["lifecycle"]:
                    conn.execute("UPDATE cognitive_memory SET confidence=?, lifecycle=?, updated_at=? WHERE id=?", (new_confidence, lifecycle, _now(), row["id"]))
                    changed += 1
        return changed

    def recall(self, query: str, limit: int = 5) -> list[CognitiveMemory]:
        if limit < 1:
            return []
        terms = set(re.findall(r"[a-z0-9_]+", query.lower()))
        if not terms:
            return []
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM cognitive_memory WHERE lifecycle != ?", (MemoryLifecycle.REJECTED.value,)).fetchall()
        ranked: list[tuple[float, CognitiveMemory]] = []
        for row in rows:
            memory = self._from_row(row)
            tokens = set(re.findall(r"[a-z0-9_]+", memory.statement.lower()))
            hits = len(terms & tokens)
            if not hits:
                continue
            lifecycle_bonus = {MemoryLifecycle.TRUSTED: 0.20, MemoryLifecycle.VERIFIED: 0.10}.get(memory.lifecycle, 0.0)
            score = hits / len(terms) + memory.confidence * 0.25 + min(memory.evidence, 20) * 0.01 + lifecycle_bonus
            ranked.append((score, memory))
        ranked.sort(key=lambda item: (item[0], item[1].confidence, item[1].evidence, item[1].updated_at), reverse=True)
        return [memory for _, memory in ranked[:limit]]
