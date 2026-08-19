"""Zero-cost SQLite strategy memory for adaptive decisions."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from runtime.adaptive_decision import OutcomeStatus, Strategy, StrategyStats


class StrategyMemory:
    def __init__(self, db_path: Path | str = Path("runtime/claude-mem-db/strategy_memory.sqlite3")) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS strategies (id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL, risk REAL NOT NULL, cost REAL NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS outcomes (id INTEGER PRIMARY KEY AUTOINCREMENT, strategy_id TEXT NOT NULL, status TEXT NOT NULL)")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def record_strategy(self, strategy: Strategy) -> str:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO strategies VALUES (?, ?, ?, ?, ?)",
                (strategy.id, strategy.name, strategy.description, strategy.risk, strategy.cost),
            )
        return strategy.id

    def _resolve_id(self, strategy_id: str) -> str:
        normalized = strategy_id.strip()
        if not normalized:
            raise ValueError("strategy_id must not be empty")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM strategies WHERE id=? OR name=?",
                (normalized, normalized),
            ).fetchone()
        if row is None:
            raise KeyError(f"strategy not found: {strategy_id}")
        return str(row[0])

    def record_outcome(self, strategy_id: str, status: OutcomeStatus) -> None:
        canonical_id = self._resolve_id(strategy_id)
        if not isinstance(status, OutcomeStatus):
            raise ValueError("status must be an OutcomeStatus")
        if status is not OutcomeStatus.UNKNOWN:
            with self._connect() as conn:
                conn.execute("INSERT INTO outcomes(strategy_id, status) VALUES (?, ?)", (canonical_id, status.value))

    def outcomes(self, strategy_id: str) -> list[OutcomeStatus]:
        canonical_id = self._resolve_id(strategy_id)
        with self._connect() as conn:
            rows = conn.execute("SELECT status FROM outcomes WHERE strategy_id=? ORDER BY id", (canonical_id,)).fetchall()
        return [OutcomeStatus(row[0]) for row in rows]

    def list_strategies(self, limit: int = 50) -> list[Strategy]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        with self._connect() as conn:
            rows = conn.execute("SELECT name, description, risk, cost FROM strategies ORDER BY id LIMIT ?", (limit,)).fetchall()
        return [Strategy(*row) for row in rows]

    def strategy_stats(self, strategy_id: str) -> StrategyStats:
        rows = self.outcomes(strategy_id)
        total = len(rows)
        if not total:
            return StrategyStats()
        success = sum(status is OutcomeStatus.SUCCESS for status in rows) / total
        partial = sum(status is OutcomeStatus.PARTIAL for status in rows) / total
        failure = sum(status is OutcomeStatus.FAILURE for status in rows) / total
        return StrategyStats(total, success, partial, failure)
