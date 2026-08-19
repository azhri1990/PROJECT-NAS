# BOB-2 Mobile Command Channel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a private authenticated BOB command channel for bounded job submission, status, cancellation, and worker heartbeat.

**Architecture:** A small FastAPI application delegates lifecycle state to the existing BOB `JobQueue` and `DeviceRegistry`, routes through `TaskRouter`, and evaluates submitted capabilities with the existing `PolicyEngine`. Authentication is bearer-token based and fail-closed; no endpoint executes arbitrary shell commands.

**Tech Stack:** Python 3.13-compatible standard library, FastAPI, existing PROJECT-NAS policy and BOB primitives, pytest.

**Spec:** `docs/superpowers/specs/2026-08-20-bob-2-command-channel-design.md`

## Global Constraints

- Existing `PolicyEngine` and `ToolGateway` remain authoritative.
- No arbitrary shell execution endpoint.
- No credentials committed to the repository.
- Local/zero-cost operation is preferred.
- Authenticated endpoints require `PROJECT_BOB_AUTH_TOKEN`.

---

### Task 1: Job cancellation lifecycle

**Files:**
- Modify: `07-AUTOMATION/bob/job_queue.py`
- Test: `tests/test_bob_command_channel.py`

- [ ] Add `CANCELLED = "cancelled"` to `JobState`.
- [ ] Add a queue cancellation method that rejects missing jobs and terminal/running jobs.
- [ ] Test successful cancellation and rejection of running/terminal cancellation.

### Task 2: Command service

**Files:**
- Create: `07-AUTOMATION/bob/command_service.py`
- Test: `tests/test_bob_command_channel.py`

- [ ] Implement `BobCommandService` with queue, registry, router, policy, and bounded audit storage.
- [ ] Implement submit/status/cancel/workers/heartbeat operations.
- [ ] Map capability strings to `runtime.policy.Capability`; reject unknown capabilities.
- [ ] Evaluate a `ToolRequest` before accepting a job.
- [ ] Route approved jobs through `TaskRouter`.
- [ ] Ensure audit records never contain authentication tokens.

### Task 3: Authenticated FastAPI surface

**Files:**
- Create: `runtime/bob_command_api.py`
- Test: `tests/test_bob_command_channel.py`

- [ ] Add bearer-token authentication with `hmac.compare_digest`.
- [ ] Add `/health`, `/jobs`, `/jobs/{job_id}`, `/jobs/{job_id}/cancel`, `/workers`, and `/workers/heartbeat`.
- [ ] Return 401 for missing/invalid credentials and 503 when the server has no configured token.
- [ ] Return bounded JSON responses only.

### Task 4: Verification and documentation

**Files:**
- Modify: `05-AI/bob/README.md`
- Modify: `05-AI/bob/architecture.md`
- Test: `tests/test_bob_command_channel.py`

- [ ] Document mobile command usage and environment configuration.
- [ ] Add tests for auth, policy denial, job lifecycle, heartbeat, and no-token fail-closed behavior.
- [ ] Run the focused test file, then the full repository test suite and doctor checks through CI.

### Task 5: Merge gate

- [ ] Inspect all CI jobs.
- [ ] Merge only when the full verification suite is green and the PR is mergeable.
- [ ] Keep secrets out of commits and logs.