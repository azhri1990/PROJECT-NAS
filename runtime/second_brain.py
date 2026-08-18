"""Local, auditable second-brain layer built on verified learning."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from runtime.adaptive_decision import AdaptiveDecisionEngine, DecisionCandidate, DecisionContext, DecisionScore, OutcomeStatus, Strategy, StrategyStats
from runtime.autonomous_learning import AutonomousLearningLoop, LearnedMemory
from runtime.cognitive_memory import CognitiveMemory, MemoryLifecycle
from runtime.learning_loop_v3 import LearningLoopV3
from runtime.strategy_memory import StrategyMemory
from runtime.verified_learning import LearningDecision, LearningType


@dataclass(frozen=True)
class BrainMemory(LearnedMemory):
    source: str
    context: str
    observed_at: str
    verification_status: str
    promotion_reason: str


class SecondBrain:
    """Personal cognitive memory plus adaptive, auditable strategy intelligence."""

    MAX_GAP_QUERIES = 20
    MAX_QUERY_CHARS = 256

    def __init__(self, db_path: Path | str = Path("runtime/claude-mem-db/second_brain.sqlite3")) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.learning = AutonomousLearningLoop(self.db_path)
        self.strategy_memory = StrategyMemory(self.db_path.parent / "strategy_memory.sqlite3")
        self.decision_engine = AdaptiveDecisionEngine()
        self._hydrate_strategy_stats()
        self._init_provenance()
        self.learning_loop = LearningLoopV3(self, self.db_path.parent / "learning_loop_v3.sqlite3")

    def _hydrate_strategy_stats(self) -> None:
        for strategy in self.strategy_memory.list_strategies():
            for status in self.strategy_memory.outcomes(strategy.id):
                self.decision_engine.observe(strategy.id, status)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_provenance(self) -> None:
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS learning_provenance (
                id INTEGER PRIMARY KEY, memory_id INTEGER, source TEXT NOT NULL,
                context TEXT NOT NULL DEFAULT '', observed_at TEXT NOT NULL,
                verification_status TEXT NOT NULL, promotion_reason TEXT NOT NULL)""")

    def learn(self, *, kind: LearningType, statement: str, confidence: float, evidence: int, verified: bool, source: str, context: str = "", contradiction: bool = False) -> LearningDecision:
        if not source.strip():
            raise ValueError("learning source must not be empty")
        decision = self.learning.learn(kind=kind, statement=statement, confidence=confidence, evidence=evidence, verified=verified, contradiction=contradiction)
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM learned_memory WHERE statement = ?", (statement.strip(),)).fetchone()
            memory_id = row["id"] if row else None
            conn.execute("""INSERT INTO learning_provenance
                (memory_id, source, context, observed_at, verification_status, promotion_reason)
                VALUES (?, ?, ?, ?, ?, ?)""", (memory_id, source.strip(), context.strip(), datetime.now(timezone.utc).isoformat(), "verified" if verified else "unverified", decision.reason))
        return decision

    def recall(self, query: str, limit: int = 5) -> list[BrainMemory]:
        memories = self.learning.recall(query, limit)
        if not memories:
            return []
        with self._connect() as conn:
            result: list[BrainMemory] = []
            for memory in memories:
                row = conn.execute("""SELECT source, context, observed_at, verification_status, promotion_reason
                    FROM learning_provenance WHERE memory_id = ? AND verification_status = 'verified'
                    ORDER BY id DESC LIMIT 1""", (memory.id,)).fetchone()
                if row:
                    result.append(BrainMemory(memory.id, memory.kind, memory.statement, memory.confidence, memory.evidence, row["source"], row["context"], row["observed_at"], row["verification_status"], row["promotion_reason"]))
            return result

    def _cognitive_memory_for(self, memory_id: int | str) -> CognitiveMemory:
        if isinstance(memory_id, bool):
            raise ValueError("memory_id must be an integer or cognitive memory id")
        if isinstance(memory_id, int):
            with self._connect() as conn:
                row = conn.execute("SELECT statement, kind FROM learned_memory WHERE id=?", (memory_id,)).fetchone()
            if row is None:
                raise KeyError(f"memory not found: {memory_id}")
            for memory in self.learning.cognitive_memory.recall(row["statement"], limit=20):
                if memory.statement == row["statement"] and memory.kind == row["kind"]:
                    return memory
            raise KeyError(f"cognitive memory not found: {memory_id}")
        if isinstance(memory_id, str) and memory_id.strip():
            return self.learning.cognitive_memory._get(memory_id.strip())
        raise ValueError("memory_id must be an integer or cognitive memory id")

    def knowledge_gaps(self, queries: list[str]) -> list[str]:
        if not isinstance(queries, list) or len(queries) > self.MAX_GAP_QUERIES:
            raise ValueError(f"queries must be a list of at most {self.MAX_GAP_QUERIES} items")
        gaps: list[str] = []
        for query in queries:
            if not isinstance(query, str) or not query.strip() or len(query.strip()) > self.MAX_QUERY_CHARS:
                raise ValueError(f"knowledge-gap query must be a non-empty string of at most {self.MAX_QUERY_CHARS} characters")
            normalized = query.strip()
            if not self.learning.recall_cognitive(normalized, limit=1):
                gaps.append(normalized)
        return gaps

    def approve_permanent(self, memory_id: int | str, *, approver: str = "user") -> CognitiveMemory:
        memory = self._cognitive_memory_for(memory_id)
        if memory.lifecycle not in {MemoryLifecycle.VERIFIED, MemoryLifecycle.TRUSTED, MemoryLifecycle.PINNED}:
            raise PermissionError("only verified or trusted memory can be pinned")
        return self.learning.cognitive_memory.approve_pinned(memory.id, approver=approver)

    def memory_history(self, memory_id: int | str) -> list[dict]:
        return self.learning.cognitive_memory.history(self._cognitive_memory_for(memory_id).id)

    def rollback_memory(self, memory_id: int | str) -> CognitiveMemory:
        return self.learning.cognitive_memory.rollback(self._cognitive_memory_for(memory_id).id)

    def review_memory(self, *, decay: float = 0.05, floor: float = 0.0) -> dict[str, int]:
        return self.learning.cognitive_memory.review(decay=decay, floor=floor)

    def record_strategy(self, strategy: Strategy) -> str:
        return self.strategy_memory.record_strategy(strategy)

    def record_outcome(self, strategy_id: str, status: OutcomeStatus) -> None:
        self.strategy_memory.record_outcome(strategy_id, status)
        self.decision_engine.observe(strategy_id, status)

    def recommend_strategy(self, candidates: list[DecisionCandidate], context: DecisionContext | None = None) -> list[DecisionScore]:
        for candidate in candidates:
            self.strategy_memory.record_strategy(candidate.strategy)
        return self.decision_engine.rank(candidates, context)

    def strategy_history(self, strategy_id: str) -> StrategyStats:
        return self.strategy_memory.strategy_stats(strategy_id)
