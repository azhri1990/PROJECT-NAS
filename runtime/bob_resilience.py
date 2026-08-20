"""Failure containment and learning primitives for PROJECT-BOB."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FailureRecord:
    job_id: str
    reason: str
    root_cause: str
    prevention: str


class FailureLedger:
    """Bounded local ledger for verified failures and prevention controls."""

    def __init__(self, limit: int = 200) -> None:
        if limit < 1:
            raise ValueError("limit must be positive")
        self._limit = limit
        self._records: list[FailureRecord] = []

    def record(self, failure: FailureRecord) -> None:
        self._records.append(failure)
        if len(self._records) > self._limit:
            del self._records[: len(self._records) - self._limit]

    def recent(self, job_id: str) -> tuple[FailureRecord, ...]:
        return tuple(record for record in self._records if record.job_id == job_id)

    def all(self) -> tuple[FailureRecord, ...]:
        return tuple(self._records)


class RetryCircuitBreaker:
    """Stop repeated failures instead of retrying indefinitely."""

    def __init__(self, max_failures: int = 3, *, ledger: FailureLedger | None = None) -> None:
        if max_failures < 1:
            raise ValueError("max_failures must be positive")
        self.max_failures = max_failures
        self.ledger = ledger or FailureLedger()
        self._failures: dict[str, int] = {}
        self._open: set[str] = set()

    def allow(self, job_id: str) -> bool:
        return job_id not in self._open

    def record_failure(self, job_id: str, *, reason: str = "executor failure") -> None:
        count = self._failures.get(job_id, 0) + 1
        self._failures[job_id] = count
        if count >= self.max_failures:
            self._open.add(job_id)
            self.ledger.record(
                FailureRecord(
                    job_id,
                    reason,
                    "repeated executor failure reached retry threshold",
                    "circuit opened; operator/root-cause review required",
                )
            )

    def record_success(self, job_id: str) -> None:
        self._failures.pop(job_id, None)
        self._open.discard(job_id)

    def is_open(self, job_id: str) -> bool:
        return job_id in self._open

    def failure_count(self, job_id: str) -> int:
        return self._failures.get(job_id, 0)
