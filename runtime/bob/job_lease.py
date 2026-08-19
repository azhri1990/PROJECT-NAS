"""Expiring, worker-owned job leases with idempotent completion."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from .worker_protocol import JobResult


@dataclass(frozen=True)
class JobLease:
    job_id: str
    worker_id: str
    lease_id: str
    issued_at: float
    expires_at: float


@dataclass(frozen=True)
class CompletionRecord:
    job_id: str
    lease_id: str
    worker_id: str
    status: str
    output: dict


class JobLeaseStore:
    def __init__(self, ttl_seconds: float = 300.0) -> None:
        if ttl_seconds <= 0:
            raise ValueError("lease ttl must be positive")
        self.ttl_seconds = ttl_seconds
        self._leases: dict[str, JobLease] = {}
        self._completed: dict[str, CompletionRecord] = {}

    def claim(self, job_id: str, worker_id: str, now: float) -> JobLease:
        if not job_id.strip() or not worker_id.strip():
            raise ValueError("job_id and worker_id must not be empty")
        for lease in self._leases.values():
            if lease.job_id == job_id and lease.lease_id not in self._completed:
                raise ValueError("job already leased")
        lease = JobLease(job_id, worker_id, uuid4().hex, now, now + self.ttl_seconds)
        self._leases[lease.lease_id] = lease
        return lease

    def renew(self, lease_id: str, worker_id: str, now: float) -> JobLease:
        lease = self._leases[lease_id]
        if lease.worker_id != worker_id:
            raise PermissionError("lease owner mismatch")
        if now > lease.expires_at:
            raise ValueError("lease expired")
        renewed = JobLease(lease.job_id, lease.worker_id, lease.lease_id, lease.issued_at, now + self.ttl_seconds)
        self._leases[lease_id] = renewed
        return renewed

    def complete(self, lease_id: str, worker_id: str, result: JobResult, now: float = 0.0) -> CompletionRecord:
        existing = self._completed.get(lease_id)
        if existing is not None:
            return existing
        lease = self._leases[lease_id]
        if lease.worker_id != worker_id or result.job_id != lease.job_id or result.lease_id != lease.lease_id:
            raise PermissionError("lease/result ownership mismatch")
        if now > lease.expires_at:
            raise ValueError("lease expired")
        record = CompletionRecord(lease.job_id, lease.lease_id, worker_id, result.status, dict(result.output))
        self._completed[lease_id] = record
        return record

    def expire(self, now: float) -> list[JobLease]:
        expired = [lease for lease in self._leases.values() if lease.expires_at < now and lease.lease_id not in self._completed]
        for lease in expired:
            self._leases.pop(lease.lease_id, None)
        return expired

    def get(self, lease_id: str) -> JobLease | None:
        return self._leases.get(lease_id)
