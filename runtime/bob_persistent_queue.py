"""Durable, local-only queue storage for PROJECT-BOB.

This layer stores job state without adding authority. Governance remains in
BobControlLoop; this module only provides persistence and recovery primitives.
"""
from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path
from uuid import uuid4

_queue = importlib.import_module("07-AUTOMATION.bob.job_queue")
Job = _queue.Job
JobState = _queue.JobState


class PersistentJobQueue:
    """SQLite-backed local queue with atomic upsert and restart recovery."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                task TEXT NOT NULL,
                capability TEXT NOT NULL,
                state TEXT NOT NULL,
                worker_id TEXT,
                reason TEXT
            )"""
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def create(self, task: str, capability: str) -> Job:
        if not isinstance(task, str) or not isinstance(capability, str):
            raise ValueError("task and capability must be strings")
        if not task.strip() or not capability.strip():
            raise ValueError("task and capability must not be empty")
        job = Job(uuid4().hex, task.strip(), capability.strip())
        return self.put(job)

    def put(self, job: Job) -> Job:
        self._conn.execute(
            """INSERT INTO jobs(job_id, task, capability, state, worker_id, reason)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(job_id) DO UPDATE SET
                 task=excluded.task, capability=excluded.capability,
                 state=excluded.state, worker_id=excluded.worker_id,
                 reason=excluded.reason""",
            (job.job_id, job.task, job.capability, job.state.value, job.worker_id, job.reason),
        )
        self._conn.commit()
        return job

    def update(self, job_id: str, **changes: object) -> Job:
        current = self.get(job_id)
        if current is None:
            raise KeyError(job_id)
        allowed = {"task", "capability", "state", "worker_id", "reason"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"unsupported job fields: {sorted(unknown)}")
        values = {
            "task": current.task,
            "capability": current.capability,
            "state": current.state,
            "worker_id": current.worker_id,
            "reason": current.reason,
        }
        values.update(changes)
        state = values["state"]
        if isinstance(state, str):
            state = JobState(state)
        job = Job(
            current.job_id,
            str(values["task"]),
            str(values["capability"]),
            state,
            values["worker_id"],
            values["reason"],
        )
        return self.put(job)

    def get(self, job_id: str) -> Job | None:
        row = self._conn.execute(
            "SELECT job_id, task, capability, state, worker_id, reason FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        return Job(row[0], row[1], row[2], JobState(row[3]), row[4], row[5])

    def queued(self, limit: int = 100) -> tuple[Job, ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        rows = self._conn.execute(
            "SELECT job_id, task, capability, state, worker_id, reason FROM jobs "
            "WHERE state = ? ORDER BY rowid LIMIT ?",
            (JobState.QUEUED.value, limit),
        ).fetchall()
        return tuple(Job(r[0], r[1], r[2], JobState(r[3]), r[4], r[5]) for r in rows)

    def recover_running(self) -> tuple[Job, ...]:
        """Move interrupted RUNNING jobs back to QUEUED after restart."""
        rows = self._conn.execute(
            "SELECT job_id, task, capability, state, worker_id, reason FROM jobs WHERE state = ?",
            (JobState.RUNNING.value,),
        ).fetchall()
        jobs = tuple(Job(r[0], r[1], r[2], JobState.QUEUED, None, "recovered after worker restart") for r in rows)
        for job in jobs:
            self.put(job)
        return jobs

    def all(self) -> tuple[Job, ...]:
        rows = self._conn.execute(
            "SELECT job_id, task, capability, state, worker_id, reason FROM jobs ORDER BY rowid"
        ).fetchall()
        return tuple(Job(r[0], r[1], r[2], JobState(r[3]), r[4], r[5]) for r in rows)
