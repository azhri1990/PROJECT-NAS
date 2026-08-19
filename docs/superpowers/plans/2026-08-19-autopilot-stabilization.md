# PROJECT-NAS AUTO PILOT Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore a verified PROJECT-NAS baseline around orchestration, cross-platform runtime behavior, and SQLite contention before PROJECT-BOB is implemented.

**Architecture:** Keep PolicyEngine and orchestration verification authoritative. Harden persistence and platform wrappers with bounded, deterministic behavior and regression tests; do not expand capabilities or introduce cloud dependencies.

**Tech Stack:** Python 3.13, SQLite, Bash, PowerShell, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-19-autopilot-stabilization-design.md`

## Global Constraints
- $0 / local-first; no paid cloud AI/API dependency.
- Unknown verification results fail closed.
- Learning cannot grant capabilities or rewrite policy/code.
- System mutation and external network capabilities remain denied or confirmation-gated.
- Inputs remain bounded and provenance is retained.
- No secrets or machine-specific paths are committed.
- Existing doctor/certification gates remain authoritative.

---

### Task 1: Establish a reproducible CI baseline

**Files:**
- Inspect: `.github/workflows/progress-check.yml`
- Inspect: `runtime/doctor.py`
- Inspect: `tests/`

**Interfaces:**
- Consumes: current `main` commit and existing CI workflow.
- Produces: an evidence-backed list of current failing tests and the smallest failing contracts to fix.

- [ ] **Step 1: Run the full CI workflow for the current head** and capture the failing job and test names.
- [ ] **Step 2: Inspect each failing test and its production dependency before changing code.**
- [ ] **Step 3: Group failures by root cause rather than patching individual assertions.**
- [ ] **Step 4: Record the root-cause groups in the implementation branch before fixing them.**

### Task 2: Harden SQLite connections against short contention

**Files:**
- Modify: `runtime/learning_loop_v3.py`
- Modify: `runtime/second_brain.py` if shared persistence behavior requires it
- Modify: the smallest affected tests under `tests/`

**Interfaces:**
- `LearningLoopV3._connect()` continues returning a row-factory-enabled `sqlite3.Connection`.
- Existing public learning-loop APIs remain unchanged.

- [ ] **Step 1: Write a failing regression test that opens competing short-lived connections and verifies the learning operation completes without an immediate `database is locked` error.**
- [ ] **Step 2: Run the focused test and verify the failure is caused by SQLite contention.**
- [ ] **Step 3: Implement the minimal bounded SQLite configuration: connection timeout, WAL mode where safe, and transactional writes without unbounded retry loops.**
- [ ] **Step 4: Run the focused persistence tests and the learning-loop test file.**
- [ ] **Step 5: Run the full pytest suite.**
- [ ] **Step 6: Commit the persistence fix with a focused message.**

### Task 3: Make runtime invocation deterministic on Windows

**Files:**
- Inspect: `runtime/project-nas.sh`
- Inspect: `runtime/progress.ps1`
- Modify only the smallest Windows-facing runtime helper required by the failing contract
- Modify: affected tests under `tests/`

**Interfaces:**
- Existing Linux/Termux shell behavior remains unchanged.
- Windows callers receive deterministic exit codes and do not depend on Bash-only path assumptions when the supported PowerShell path is used.

- [ ] **Step 1: Add a regression test for the observed Windows invocation contract, using path-independent repository resolution rather than a developer-specific absolute path.**
- [ ] **Step 2: Run the focused test and verify it fails against the current implementation.**
- [ ] **Step 3: Implement the minimal platform-specific correction without duplicating runtime business logic.**
- [ ] **Step 4: Run the focused tests plus shell syntax validation.**
- [ ] **Step 5: Run the full pytest suite and doctor diagnostics.**
- [ ] **Step 6: Commit the Windows runtime correction.**

### Task 4: Reconcile orchestration contracts

**Files:**
- Inspect: `runtime/cognitive_orchestrator.py`
- Inspect: `runtime/orchestration_tools.py`
- Inspect: `runtime/orchestration_policy.py`
- Inspect: `runtime/orchestration_verifier.py`
- Modify: the smallest affected runtime file
- Modify: `tests/test_cognitive_orchestrator.py` and any directly affected orchestration tests

**Interfaces:**
- `CognitiveOrchestrator.execute(...)` continues returning `CognitiveOutcome`.
- `ToolRegistry.execute(...)` remains the capability/policy authority.
- `verify_result(...)` remains fail-closed for unknown tool contracts.

- [ ] **Step 1: Write or refine one failing regression test per actual root cause discovered in Task 1.**
- [ ] **Step 2: Run those tests and verify each fails for the intended reason.**
- [ ] **Step 3: Implement only the minimal contract correction.**
- [ ] **Step 4: Run focused orchestration tests.**
- [ ] **Step 5: Run the full suite and inspect audit/policy behavior for regressions.**
- [ ] **Step 6: Commit the orchestration correction.**

### Task 5: Final verification and PROJECT-BOB handoff

**Files:**
- Inspect: `ACTION-PLAN.md`
- Modify: `ACTION-PLAN.md` only if verified status materially changes
- Create: `docs/superpowers/plans/2026-08-19-project-bob-foundation.md` only after the stabilization gate is green

**Interfaces:**
- No runtime interface changes in this task.

- [ ] **Step 1: Run full pytest, compileall, shell syntax, doctor, and repository whitespace checks.**
- [ ] **Step 2: Review the final diff for policy, provenance, path, and secret-handling regressions.**
- [ ] **Step 3: Confirm GitHub Actions is green for the implementation branch.**
- [ ] **Step 4: Create a PROJECT-BOB foundation plan that consumes the verified NAS interfaces rather than bypassing them.**
- [ ] **Step 5: Open a pull request for review; do not merge automatically.**

## Rulings
- **Ruling:** Stabilization precedes BOB implementation — because BOB must build against a verified NAS contract; building a second automation layer on a failing baseline multiplies debugging surface.
- **Ruling:** CI is the repository-level verification authority — because the available GitHub execution environment can verify the full Linux suite, while Windows/Termux remain local follow-up environments.
- **Ruling:** No broad refactor — because current failures should be corrected at their actual contract boundaries rather than hidden behind architectural churn.
