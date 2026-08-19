# BOB-5 Android Worker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deployable Android/Termux BOB worker that can authenticate, register, heartbeat, claim policy-approved jobs, report idempotent results, and recover safely after connectivity loss.

**Architecture:** The worker is a thin client around the existing BOB-4 HTTP worker protocol. It stores only worker-scoped configuration and resumable local state, never a master NAS credential; execution remains constrained by the NAS PolicyEngine/ToolGateway.

**Tech Stack:** Python 3, Termux, existing PROJECT-NAS BOB HTTP protocol, local JSON/SQLite state as appropriate, pytest.

**Spec:** BOB-5 design approved in conversation on 2026-08-20.

## Global Constraints

- Zero-cost architecture; no paid service is required.
- Android/Termux is the first real worker target.
- No arbitrary public shell endpoint.
- Worker capability does not grant permission.
- NAS PolicyEngine/ToolGateway remains authoritative.
- Credentials must never be committed to the repository.
- Job execution must be lease-bound and idempotent.
- Offline operation must fail closed and reconcile safely after reconnect.

---

### Task 1: Worker package contract

**Files:**
- Create: `runtime/bob/android_worker.py`
- Create: `tests/test_bob_android_worker.py`

**Interfaces:**
- Produces `AndroidWorkerConfig`, `AndroidWorker`, and `WorkerState` interfaces used by later tasks.

- [ ] Step 1: Write failing tests for configuration validation and worker identity.
- [ ] Step 2: Run `pytest tests/test_bob_android_worker.py -q` and verify collection/failure is expected.
- [ ] Step 3: Implement minimal configuration and identity validation without storing secrets in source.
- [ ] Step 4: Run the focused tests and require PASS.
- [ ] Step 5: Commit with `feat(bob): add android worker contract`.

### Task 2: Secure registration and heartbeat

**Files:**
- Modify: `runtime/bob/android_worker.py`
- Test: `tests/test_bob_android_worker.py`

**Interfaces:**
- `register()` authenticates the worker and records server identity.
- `heartbeat()` sends worker identity, capabilities, and lease state.

- [ ] Step 1: Add failing tests for successful registration, invalid authentication, and heartbeat expiry.
- [ ] Step 2: Run focused tests and confirm failure.
- [ ] Step 3: Implement authenticated registration/heartbeat using the existing BOB-4 protocol.
- [ ] Step 4: Verify failures are fail-closed and no bearer token is written to logs.
- [ ] Step 5: Run focused tests and require PASS.
- [ ] Step 6: Commit with `feat(bob): add android worker registration`.

### Task 3: Job polling and policy-gated execution

**Files:**
- Modify: `runtime/bob/android_worker.py`
- Test: `tests/test_bob_android_worker.py`

**Interfaces:**
- `poll_and_claim()` returns only jobs leased to this worker.
- `execute_job()` accepts only an already-authorized lease and delegates authorization-sensitive decisions to the NAS policy boundary.

- [ ] Step 1: Add failing tests for capability mismatch, expired lease, policy denial, and successful claim.
- [ ] Step 2: Run focused tests and confirm failure.
- [ ] Step 3: Implement bounded polling and lease validation; never accept client-supplied authorization flags.
- [ ] Step 4: Run focused tests and require PASS.
- [ ] Step 5: Commit with `feat(bob): add android job polling`.

### Task 4: Idempotent result reporting and local recovery state

**Files:**
- Modify: `runtime/bob/android_worker.py`
- Create: `runtime/bob/android_state.py`
- Test: `tests/test_bob_android_worker.py`

**Interfaces:**
- `record_result()` persists a resumable result intent locally.
- `flush_results()` retries safely and treats already-recorded results as idempotent.
- `reconcile()` restores safe state after reconnect.

- [ ] Step 1: Add failing tests for duplicate result submission and interrupted connectivity.
- [ ] Step 2: Run focused tests and confirm failure.
- [ ] Step 3: Implement local state with atomic writes and bounded retry metadata.
- [ ] Step 4: Ensure secrets are excluded from persisted state.
- [ ] Step 5: Run focused tests and require PASS.
- [ ] Step 6: Commit with `feat(bob): add android worker recovery state`.

### Task 5: Termux bootstrap

**Files:**
- Create: `runtime/bootstrap_bob_android.sh`
- Create: `docs/BOB-5-ANDROID-SETUP.md`
- Test: `tests/test_bob_android_bootstrap.py`

**Interfaces:**
- Bootstrap installs/validates the worker runtime without requiring a paid dependency.
- Configuration is supplied through environment/local config outside tracked source.

- [ ] Step 1: Add tests for safe bootstrap path handling and required environment variables.
- [ ] Step 2: Run bootstrap tests and verify failure before implementation.
- [ ] Step 3: Implement idempotent Termux bootstrap using the repository's existing runtime requirements.
- [ ] Step 4: Document the exact mobile setup and safe credential handling.
- [ ] Step 5: Run bootstrap tests and require PASS.
- [ ] Step 6: Commit with `feat(bob): add termux worker bootstrap`.

### Task 6: Integration and CI gate

**Files:**
- Modify: `tests/test_bob_android_worker.py`
- Modify: `tests/test_bob_android_bootstrap.py`
- Modify only existing CI configuration if a concrete integration gap is discovered.

**Interfaces:**
- The Android worker must remain compatible with BOB-4 and the full PROJECT-NAS regression suite.

- [ ] Step 1: Run `python -m pytest tests/test_bob_android_worker.py tests/test_bob_android_bootstrap.py -q`.
- [ ] Step 2: Run the complete `python -m pytest -q` suite.
- [ ] Step 3: Run repository doctor/static checks used by existing CI.
- [ ] Step 4: Fix only actual failures; do not weaken tests or bypass policy enforcement.
- [ ] Step 5: Commit final integration changes.
- [ ] Step 6: Push the branch and require all GitHub Actions workflows to pass before opening/merging the PR.

## Verification Gate

BOB-5 cannot merge until Android worker tests, full PROJECT-NAS regression tests, runtime smoke/integration checks, and security-boundary tests are green.
