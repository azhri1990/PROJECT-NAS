# Core Read Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose a single governed local intent router over the existing read-only ToolGateway without creating a second execution path.

**Architecture:** The router classifies a small allowlisted set of explicit read intents and delegates execution to `ToolGateway`. It never executes shell commands, performs network access, writes repository state, or bypasses the policy engine. All tool input remains bounded by the existing gateway validators and all execution is audited by the gateway.

**Tech Stack:** Python 3.13-compatible standard library, existing PROJECT-NAS `PolicyEngine`, `ToolGateway`, SQLite memory adapter, FastAPI backend.

## Global Constraints

- $0/local-first; no required paid API, cloud AI, or token-credit dependency.
- Use the existing `ToolGateway` as the sole execution boundary.
- Process execution and network access remain denied by default.
- Repository/device writes require explicit approval and are not exposed by this tranche.
- Preserve Termux/Android compatibility and pure-Python runtime dependencies.
- All new behavior requires regression tests.

---

### Task 1: Governed Intent Router

**Files:**
- Create: `runtime/orchestrator.py`
- Test: `tests/test_orchestrator.py`

**Interfaces:**
- Consumes: `ToolGateway.execute(name, payload)`.
- Produces: `IntentRouter.handle(intent, payload) -> dict` for four explicit read intents: `health`, `progress`, `memory`, `prompt`.

- [ ] **Step 1: Write failing tests** for exact intent mapping, rejection of unknown intents, and preservation of gateway errors.
- [ ] **Step 2: Run focused tests and confirm failure.**
- [ ] **Step 3: Implement the minimal router with a fixed mapping and no dynamic tool-name construction.**
- [ ] **Step 4: Run focused tests and confirm pass.**
- [ ] **Step 5: Commit the router and tests.**

### Task 2: Backend Integration

**Files:**
- Modify: `runtime/backend.py`
- Test: `tests/test_backend.py`

**Interfaces:**
- Consumes: `IntentRouter.handle`.
- Produces: `POST /intent/{intent}` for the four read-only intents.

- [ ] **Step 1: Add failing endpoint tests.**
- [ ] **Step 2: Verify the endpoint tests fail before integration.**
- [ ] **Step 3: Add the endpoint using the existing gateway-backed router.**
- [ ] **Step 4: Add explicit rejection tests for unsupported intents and privileged tool names.**
- [ ] **Step 5: Run backend-focused tests.**
- [ ] **Step 6: Commit the integration.**

### Task 3: Verification

**Files:**
- Modify: `tests/test_tool_gateway.py` only if a regression is discovered.

- [ ] **Step 1: Run the complete pytest suite.**
- [ ] **Step 2: Run Python compilation and shell syntax checks.**
- [ ] **Step 3: Run `runtime/doctor.py`.**
- [ ] **Step 4: Verify no new runtime dependency is introduced.**
- [ ] **Step 5: Review the diff for privilege-boundary bypasses and unbounded input.**
- [ ] **Step 6: Open a PR only after all verification gates pass.**
