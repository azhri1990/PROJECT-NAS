from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from runtime.bob.audit import WorkerAudit
from runtime.bob.job_lease import JobLeaseStore
from runtime.bob.worker_protocol import JobResult, WorkerRegistration
from runtime.bob.worker_registry import WorkerRegistry
from runtime.bob.worker_service import WorkerService


def test_worker_registration_contract_requires_identity_and_supported_platform() -> None:
    with pytest.raises(ValueError):
        WorkerRegistration("", "android")
    with pytest.raises(ValueError):
        WorkerRegistration("w1", "server")  # type: ignore[arg-type]


def test_job_result_carries_job_and_lease_identity() -> None:
    result = JobResult("j1", "l1", "succeeded", {"ok": True})
    assert result.job_id == "j1"
    assert result.lease_id == "l1"


def test_registration_heartbeat_and_expiry() -> None:
    registry = WorkerRegistry(heartbeat_timeout_seconds=30)
    registry.register_worker(WorkerRegistration("android-1", "android", frozenset({"read_repository"})), now=100)
    record = registry.heartbeat("android-1", "android-1", now=110)
    assert record.status == "available"
    assert registry.expire_workers(141) == ["android-1"]
    assert registry.get("android-1").status == "offline"


def test_lease_completion_is_idempotent() -> None:
    leases = JobLeaseStore(ttl_seconds=30)
    lease = leases.claim("job-1", "pc-1", now=100)
    result = JobResult("job-1", lease.lease_id, "succeeded", {"ok": True})
    first = leases.complete(lease.lease_id, "pc-1", result, now=110)
    second = leases.complete(lease.lease_id, "pc-1", result, now=120)
    assert second == first


def test_expired_lease_is_reclaimable() -> None:
    leases = JobLeaseStore(ttl_seconds=30)
    first = leases.claim("job-1", "android-1", now=100)
    assert leases.expire(131) == [first]
    second = leases.claim("job-1", "pc-1", now=132)
    assert second.worker_id == "pc-1"


def test_policy_denial_prevents_execute_process_claim() -> None:
    registry = WorkerRegistry()
    registry.register_worker(WorkerRegistration("pc-1", "pc", frozenset({"execute_process"})), now=100)
    service = WorkerService(registry, JobLeaseStore(), WorkerAudit(), auth_token="secret")
    with pytest.raises(PermissionError, match="denied"):
        service.claim("job-1", "pc-1", "execute_process", now=101)


def test_capability_is_not_policy_authority() -> None:
    registry = WorkerRegistry()
    registry.register_worker(WorkerRegistration("pc-1", "pc", frozenset({"write_repository"})), now=100)
    service = WorkerService(registry, JobLeaseStore(), WorkerAudit(), auth_token="secret")
    with pytest.raises(PermissionError):
        service.claim("job-1", "pc-1", "write_repository", now=101)


def test_allowed_read_claim_and_result() -> None:
    registry = WorkerRegistry()
    audit = WorkerAudit()
    service = WorkerService(registry, JobLeaseStore(ttl_seconds=30), audit, auth_token="secret")
    registry.register_worker(WorkerRegistration("android-1", "android", frozenset({"read_repository"})), now=100)
    claim = service.claim("job-1", "android-1", "read_repository", now=101)
    result = service.result("android-1", JobResult("job-1", claim["lease_id"], "succeeded", {"ok": True}), now=102)
    assert result["status"] == "succeeded"
    assert any(event.event_type == "job_completed" for event in audit.events())


def test_recovery_releases_expired_job_and_audits_requeue() -> None:
    audit = WorkerAudit()
    service = WorkerService(WorkerRegistry(), JobLeaseStore(ttl_seconds=30), audit, auth_token="secret")
    service.registry.register_worker(WorkerRegistration("android-1", "android", frozenset({"read_repository"})), now=100)
    service.claim("job-1", "android-1", "read_repository", now=100)
    assert service.recover(131) == ["job-1"]
    assert service.recover(132) == []
    assert any(event.event_type == "job_requeued" for event in audit.events())
