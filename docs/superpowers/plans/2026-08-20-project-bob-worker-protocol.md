# PROJECT-BOB Worker Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a secure HTTP worker protocol that lets Android/Termux, PC, and tablet workers register, heartbeat, claim authorized jobs, report results, and recover safely from disconnects.

**Architecture:** BOB owns worker identity, leases, routing, and lifecycle state. Workers communicate over authenticated HTTP; NAS PolicyEngine/ToolGateway remains the final authority for execution. Jobs use expiring leases and idempotency keys so worker loss can trigger safe requeue without accepting duplicate completion.

**Tech Stack:** Existing PROJECT-NAS Python runtime, FastAPI/HTTP stack already present, existing BOB control-plane primitives, pytest, GitHub Actions.

**Spec:** BOB-4 Distributed Worker Protocol design approved in conversation; implementation must preserve the existing NAS policy boundary and zero-cost/local-first architecture.

## Global Constraints

- No arbitrary public shell endpoint.
- Worker capability declarations never grant execution permission.
- NAS PolicyEngine/ToolGateway remains authoritative.
- Authentication fails closed when credentials are absent or invalid.
- Worker leases expire and become reclaimable after timeout.
- Result submission is idempotent by job/lease identity.
- Android, PC, and tablet are protocol peers; no device is inherently trusted.
- No paid API, cloud GPU, or mandatory external dependency is introduced.
- All new behavior requires automated tests and CI verification before merge.

---

### Task 1: Define worker protocol contracts

**Files:**
- Create: `runtime/bob/worker_protocol.py`
- Test: `tests/test_bob_worker_protocol.py`

**Interfaces:**
- Produces typed request/result contracts for registration, heartbeat, job claim, result reporting, and lease metadata.

- [ ] **Step 1: Write failing tests**

```python
def test_worker_registration_contract_requires_identity_and_capabilities():
    from runtime.bob.worker_protocol import WorkerRegistration
    with pytest.raises(ValueError):
        WorkerRegistration(worker_id="", platform="android", capabilities=[])


def test_job_result_contract_carries_job_and_lease_identity():
    from runtime.bob.worker_protocol import JobResult
    result = JobResult(job_id="j1", lease_id="l1", status="succeeded", output={})
    assert result.job_id == "j1"
    assert result.lease_id == "l1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_bob_worker_protocol.py`
Expected: FAIL because the protocol module does not yet exist.

- [ ] **Step 3: Implement minimal typed contracts**

Define explicit validation for non-empty worker/job/lease identifiers, supported platform values (`android`, `pc`, `tablet`), and result statuses (`succeeded`, `failed`, `cancelled`). Keep contracts independent from transport code.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_bob_worker_protocol.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/bob/worker_protocol.py tests/test_bob_worker_protocol.py
git commit -m "feat(bob): define worker protocol contracts"
```

### Task 2: Add worker registry lifecycle

**Files:**
- Create or modify: `runtime/bob/worker_registry.py`
- Test: `tests/test_bob_worker_registry.py`

**Interfaces:**
- `register_worker(registration) -> WorkerRecord`
- `heartbeat(worker_id, auth_identity) -> WorkerRecord`
- `list_workers() -> list[WorkerRecord]`
- `expire_workers(now) -> list[str]`

- [ ] **Step 1: Write failing tests**

```python
def test_registration_and_heartbeat_update_last_seen():
    registry = WorkerRegistry()
    registry.register_worker(registration)
    record = registry.heartbeat("android-1", auth_identity="android-1")
    assert record.worker_id == "android-1"
    assert record.status == "available"


def test_expired_worker_is_not_available():
    registry = WorkerRegistry(heartbeat_timeout_seconds=30)
    registry.register_worker(registration)
    expired = registry.expire_workers(now=100)
    assert "android-1" in expired
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_bob_worker_registry.py`
Expected: FAIL until lifecycle methods exist.

- [ ] **Step 3: Implement lifecycle state**

Store worker identity, platform, capabilities, status, last-seen timestamp, and resource snapshot. Reject heartbeat from an identity different from the registered worker identity.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_bob_worker_registry.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/bob/worker_registry.py tests/test_bob_worker_registry.py
git commit -m "feat(bob): add worker registry lifecycle"
```

### Task 3: Add job leasing and idempotent completion

**Files:**
- Create: `runtime/bob/job_lease.py`
- Test: `tests/test_bob_job_lease.py`

**Interfaces:**
- `claim(job_id, worker_id, now) -> JobLease`
- `renew(lease_id, worker_id, now) -> JobLease`
- `complete(lease_id, worker_id, result) -> CompletionRecord`
- `expire(now) -> list[JobLease]`

- [ ] **Step 1: Write failing tests**

```python
def test_claim_creates_expiring_lease():
    lease = leases.claim("job-1", "pc-1", now=100)
    assert lease.job_id == "job-1"
    assert lease.expires_at > 100


def test_duplicate_completion_is_idempotent():
    first = leases.complete("lease-1", "pc-1", success_result)
    second = leases.complete("lease-1", "pc-1", success_result)
    assert second == first
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_bob_job_lease.py`
Expected: FAIL until lease handling exists.

- [ ] **Step 3: Implement bounded leases**

Generate opaque lease IDs, enforce worker ownership, reject completion after lease expiry unless the job was already completed, and preserve one canonical completion record for repeated submissions.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_bob_job_lease.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/bob/job_lease.py tests/test_bob_job_lease.py
git commit -m "feat(bob): add expiring job leases"
```

### Task 4: Add authenticated worker HTTP service

**Files:**
- Create: `runtime/bob/worker_service.py`
- Test: `tests/test_bob_worker_service.py`

**Interfaces:**
- `create_worker_app(registry, leases, policy_gateway, auth)` returns the FastAPI application.
- Endpoints: `POST /workers/register`, `POST /workers/heartbeat`, `POST /jobs/claim`, `POST /jobs/result`, `GET /workers`.

- [ ] **Step 1: Write failing tests**

```python
def test_missing_auth_is_rejected(client):
    response = client.post("/workers/register", json=registration_payload)
    assert response.status_code == 401


def test_registered_worker_can_heartbeat(client, token):
    response = client.post("/workers/heartbeat", headers={"Authorization": f"Bearer {token}"}, json={"worker_id": "android-1"})
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_bob_worker_service.py`
Expected: FAIL until the HTTP service exists.

- [ ] **Step 3: Implement authentication and transport**

Use the existing BOB bearer-token convention. Require authentication on every worker endpoint, validate worker identity, route claims through the existing task/job system, and never expose a shell/command endpoint.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_bob_worker_service.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/bob/worker_service.py tests/test_bob_worker_service.py
git commit -m "feat(bob): add authenticated worker service"
```

### Task 5: Integrate NAS policy before execution handoff

**Files:**
- Modify: `runtime/bob/worker_service.py`
- Modify: existing NAS policy integration module identified during implementation
- Test: `tests/test_bob_worker_policy.py`

**Interfaces:**
- Worker claim must produce an explicit policy decision before returning executable job data.

- [ ] **Step 1: Write failing tests**

```python
def test_policy_denial_prevents_job_claim(client, denied_policy):
    response = client.post("/jobs/claim", headers=auth_headers, json={"worker_id": "pc-1"})
    assert response.status_code == 403


def test_capability_does_not_override_policy(client, denied_policy):
    response = client.post("/jobs/claim", headers=auth_headers, json={"worker_id": "pc-1", "capabilities": ["shell"]})
    assert response.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_bob_worker_policy.py`
Expected: FAIL until policy enforcement is wired into claims.

- [ ] **Step 3: Implement policy-gated handoff**

Call the existing NAS policy authority before a worker receives executable task details. Treat any missing, malformed, or denied policy decision as deny.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_bob_worker_policy.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/bob/worker_service.py tests/test_bob_worker_policy.py
 git commit -m "security(bob): enforce NAS policy on worker claims"
```

### Task 6: Add result reporting, recovery, and audit

**Files:**
- Create or modify: `runtime/bob/audit.py`
- Modify: `runtime/bob/worker_service.py`
- Test: `tests/test_bob_worker_recovery.py`

**Interfaces:**
- `record_worker_event(event) -> None`
- Expired leases return to the existing BOB queue exactly once.

- [ ] **Step 1: Write failing tests**

```python
def test_worker_loss_requeues_expired_job_once():
    lease = leases.claim("job-1", "android-1", now=100)
    requeued = coordinator.recover(now=lease.expires_at + 1)
    assert requeued == ["job-1"]
    assert coordinator.recover(now=lease.expires_at + 2) == []


def test_result_and_recovery_are_audited():
    events = audit.events()
    assert any(event.type == "job_requeued" for event in events)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_bob_worker_recovery.py`
Expected: FAIL until recovery/audit integration exists.

- [ ] **Step 3: Implement recovery and audit**

On lease expiry, mark the worker unavailable, requeue the job once, and record worker registration, heartbeat, claim, completion, denial, expiry, and requeue events without storing bearer tokens.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_bob_worker_recovery.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/bob tests/test_bob_worker_recovery.py
 git commit -m "feat(bob): add worker recovery and audit"
```

### Task 7: Add worker adapters and end-to-end protocol coverage

**Files:**
- Create: `runtime/bob/worker_client.py`
- Create: `runtime/bob/workers/android_termux.py`
- Create: `runtime/bob/workers/pc.py`
- Create: `runtime/bob/workers/tablet.py`
- Test: `tests/test_bob_worker_e2e.py`

**Interfaces:**
- `WorkerClient.register() -> WorkerRegistration`
- `WorkerClient.heartbeat() -> WorkerRecord`
- `WorkerClient.claim() -> JobLease | None`
- `WorkerClient.report(result) -> CompletionRecord`

- [ ] **Step 1: Write failing end-to-end test**

```python
def test_worker_register_claim_execute_report_round_trip():
    worker = WorkerClient(server, worker_id="android-1", platform="android", capabilities=["python"])
    worker.register()
    worker.heartbeat()
    lease = worker.claim()
    assert lease is not None
    result = worker.report(JobResult(job_id=lease.job_id, lease_id=lease.lease_id, status="succeeded", output={"ok": True}))
    assert result.status == "succeeded"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_bob_worker_e2e.py`
Expected: FAIL until the worker client exists.

- [ ] **Step 3: Implement platform-neutral client and thin adapters**

The adapters only describe platform/capabilities and transport configuration. They must not contain privileged execution logic or embedded credentials.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q tests/test_bob_worker_e2e.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/bob tests/test_bob_worker_e2e.py
 git commit -m "feat(bob): add distributed worker clients"
```

### Task 8: Document operations and run full verification

**Files:**
- Create: `docs/BOB-4-WORKER-PROTOCOL.md`
- Modify: `README.md` or the existing BOB documentation entrypoint
- Test: existing CI suite plus BOB worker tests

**Interfaces:**
- Documentation defines registration, heartbeat, lease, result, recovery, authentication, and mobile/PC/tablet bootstrap behavior.

- [ ] **Step 1: Write operational documentation**

Document the exact HTTP endpoints, authentication header, request/response examples, lease semantics, failure states, and safe network exposure. State explicitly that BOB worker registration does not grant execution permission.

- [ ] **Step 2: Run focused worker suite**

Run: `python -m pytest -q tests/test_bob_worker_protocol.py tests/test_bob_worker_registry.py tests/test_bob_job_lease.py tests/test_bob_worker_service.py tests/test_bob_worker_policy.py tests/test_bob_worker_recovery.py tests/test_bob_worker_e2e.py`
Expected: PASS.

- [ ] **Step 3: Run full regression suite**

Run: `python -m pytest -q`
Expected: PASS with no regressions.

- [ ] **Step 4: Run project doctor/static checks**

Run the repository's existing CI-equivalent doctor, compilation, whitespace, and integration commands defined by the current GitHub Actions workflows.
Expected: PASS.

- [ ] **Step 5: Commit documentation**

```bash
git add docs/BOB-4-WORKER-PROTOCOL.md README.md
 git commit -m "docs(bob): document distributed worker protocol"
```

- [ ] **Step 6: Open PR and require green CI**

Open a draft PR from `feat/project-bob-worker-protocol` to `main`. Do not merge until all repository workflows pass and the PR is mergeable.

## Spec Coverage Self-Review

- Worker registration: Task 2.
- Secure heartbeat: Tasks 2 and 4.
- Capability advertisement: Tasks 1 and 2.
- Job leasing: Task 3.
- Policy-gated execution handoff: Task 5.
- Result reporting: Tasks 4 and 7.
- Lease expiry/requeue: Task 6.
- Idempotency/duplicate protection: Task 3.
- Android/PC/tablet adapters: Task 7.
- Audit trail: Task 6.
- End-to-end tests: Task 7.
- CI verification: Task 8.
- No arbitrary shell/public execution endpoint: Global Constraints and Tasks 4-5.
- Zero-cost/local-first architecture: Global Constraints.

## Type Consistency Self-Review

`WorkerRegistration`, `WorkerRecord`, `JobLease`, and `JobResult` are defined by Task 1 and consumed by later tasks. Registry, lease, service, and client method names are fixed in each task before implementation. No later task depends on an undefined interface.
