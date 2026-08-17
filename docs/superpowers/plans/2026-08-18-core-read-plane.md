# Core Read Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose a single governed local intent router over the existing read-only ToolGateway without creating a second execution path.

**Architecture:** A fixed allowlist maps four read intents to existing ToolGateway names. The router never executes privileged operations or constructs arbitrary tool names. FastAPI exposes only the router; validation and audit remain centralized in ToolGateway.

**Tech Stack:** Python 3.13-compatible standard library, existing PolicyEngine, ToolGateway, SQLite memory adapter, FastAPI.

## Global Constraints

- $0/local-first; no required paid API, cloud AI, or token-credit dependency.
- Use the existing ToolGateway as the sole execution boundary.
- Process execution and network access remain denied by default.
- Repository/device writes require explicit approval and are not exposed by this tranche.
- Preserve Termux/Android compatibility and pure-Python runtime dependencies.
- All new behavior requires regression tests.

---

### Task 1: Governed Intent Router

**Files:** Create `runtime/orchestrator.py`; test `tests/test_orchestrator.py`.

- [ ] Write failing tests for exact mapping, unknown-intent rejection, payload validation, and gateway error propagation.
- [ ] Run focused tests and confirm failure.
- [ ] Implement fixed intent-to-tool mapping through `ToolGateway`.
- [ ] Run focused tests and confirm pass.
- [ ] Commit.

### Task 2: Backend Integration

**Files:** Modify `runtime/backend.py`; test `tests/test_backend.py`.

- [ ] Add failing endpoint tests for four read intents and unsupported intents.
- [ ] Run focused tests and confirm failure.
- [ ] Add `POST /intent/{intent}` backed exclusively by `IntentRouter`.
- [ ] Verify privileged tool names cannot be selected through the endpoint.
- [ ] Run backend-focused tests.
- [ ] Commit.

### Task 3: Verification

- [ ] Run full pytest suite.
- [ ] Run Python compilation and shell syntax checks.
- [ ] Run `runtime/doctor.py`.
- [ ] Verify no new runtime dependency.
- [ ] Review privilege boundary and input bounds.
- [ ] Open PR only after all gates pass.
