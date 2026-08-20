"""Bounded autonomous task/control loop for PROJECT-BOB."""
from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

from runtime.autopilot_governance import AutopilotGovernance, DecisionClass
from runtime.bob_resilience import FailureLedger, RetryCircuitBreaker
from runtime.policy import Capability, PolicyEngine, RiskLevel, ToolRequest

_bob_queue = importlib.import_module("07-AUTOMATION.bob.job_queue")
Job = _bob_queue.Job
JobQueue = _bob_queue.JobQueue
JobState = _bob_queue.JobState


class BobControlLoop:
    """Run bounded local jobs without bypassing NAS governance or retry controls."""

    def __init__(
        self,
        *,
        policy: PolicyEngine | None = None,
        executor: Callable[[Job], Any] | None = None,
        queue: JobQueue | None = None,
        audit_limit: int = 200,
        max_failures: int = 3,
        failure_ledger: FailureLedger | None = None,
    ) -> None:
        if audit_limit < 1:
            raise ValueError("audit_limit must be positive")
        self.policy = policy or PolicyEngine()
        self.governance = AutopilotGovernance(self.policy)
        self.executor = executor or (lambda job: True)
        self.queue = queue or JobQueue()
        self.audit: list[dict[str, Any]] = []
        self._audit_limit = audit_limit
        self.failure_ledger = failure_ledger or FailureLedger()
        self.circuit = RetryCircuitBreaker(max_failures=max_failures, ledger=self.failure_ledger)

    def _record(self, event: str, **data: Any) -> None:
        self.audit.append({"event": event, **data})
        if len(self.audit) > self._audit_limit:
            del self.audit[: len(self.audit) - self._audit_limit]

    @staticmethod
    def _capability(value: str) -> Capability:
        try:
            return Capability(value.strip())
        except (AttributeError, ValueError) as exc:
            raise ValueError(f"unknown capability: {value}") from exc

    @staticmethod
    def _risk(value: str) -> RiskLevel:
        try:
            return RiskLevel(value.strip())
        except (AttributeError, ValueError) as exc:
            raise ValueError(f"unknown risk level: {value}") from exc

    def submit(self, task: str, capability: str, *, risk: str = RiskLevel.LOW.value) -> Job:
        if not isinstance(task, str) or not task.strip() or len(task.strip()) > 4000:
            raise ValueError("task must be a non-empty string of at most 4000 characters")
        cap = self._capability(capability)
        risk_level = self._risk(risk)
        request = ToolRequest(f"bob.job.{cap.value}", cap, risk_level, {"task": task.strip()})
        decision = self.governance.classify(request)
        self._record("governance", capability=cap.value, risk=risk_level.value, classification=decision.classification.value, reason=decision.reason)
        job = self.queue.create(task.strip(), cap.value)
        if decision.classification is not DecisionClass.AUTO:
            return self.queue.update(job.job_id, state=JobState.BLOCKED, reason=decision.reason)
        return self.queue.update(job.job_id, state=JobState.QUEUED)

    def run_once(self, job_id: str) -> Job:
        job = self.queue.get(job_id)
        if job is None:
            raise KeyError(job_id)
        if job.state is JobState.BLOCKED:
            self._record("blocked", job_id=job.job_id, reason=job.reason)
            return job
        if job.state is not JobState.QUEUED:
            raise ValueError(f"job cannot run from state: {job.state.value}")
        if not self.circuit.allow(job.job_id):
            blocked = self.queue.update(
                job.job_id,
                state=JobState.BLOCKED,
                reason="retry circuit open; root-cause review required",
            )
            self._record("circuit_open", job_id=job.job_id, reason=blocked.reason)
            return blocked
        running = self.queue.update(job.job_id, state=JobState.RUNNING)
        self._record("running", job_id=running.job_id)
        try:
            success = bool(self.executor(running))
        except Exception as exc:
            reason = f"executor error: {type(exc).__name__}"
            failed = self.queue.update(job.job_id, state=JobState.FAILED, reason=reason)
            self.circuit.record_failure(job.job_id, reason=reason)
            self._record("failure", job_id=job.job_id, reason=failed.reason, failure_count=self.circuit.failure_count(job.job_id))
            return failed
        if not success:
            reason = "executor reported failure"
            failed = self.queue.update(job.job_id, state=JobState.FAILED, reason=reason)
            self.circuit.record_failure(job.job_id, reason=reason)
            self._record("failure", job_id=job.job_id, reason=failed.reason, failure_count=self.circuit.failure_count(job.job_id))
            return failed
        succeeded = self.queue.update(job.job_id, state=JobState.SUCCEEDED, reason=None)
        self.circuit.record_success(job.job_id)
        self._record("succeeded", job_id=job.job_id)
        return succeeded
