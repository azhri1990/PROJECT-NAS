# PROJECT-BOB Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing BOB watchdog and learning components into an evidence-driven, bounded autonomous control plane that can safely build and verify PROJECT-NAS.

**Architecture:** Keep BOB's lifecycle state, failure learning, task orchestration, and verification as separate focused components. BOB never bypasses NAS policy or directly grants authorization; execution remains behind existing policy/tool boundaries.

**Tech Stack:** Python 3.12+, pytest, existing PROJECT-NAS runtime modules, GitHub Actions, local JSON/SQLite state only.

**Spec:** `docs/superpowers/specs/2026-08-20-bob-nas-jarvis-architecture.md`

## Global Constraints

- Zero-cost/local-first; no paid API or cloud AI dependency.
- Exact-revision evidence is required before `VERIFIED` is reported.
- Known failure classes must escalate instead of silently looping.
- Fail closed on verification, authorization, or safety uncertainty.
- Existing NAS policy/security boundaries remain authoritative.
- Routine operation must not require repeated human approval.

---

### Task 1: Make verification state explicit

**Files:**
- Create: `runtime/bob_verification.py`
- Test: `tests/test_bob_verification.py`

**Interfaces:**
- Consumes: repository revision, workflow name, run existence/status, run revision.
- Produces: `VerificationState` with states `NOT_TRIGGERED`, `RUNNING`, `FAILED`, `VERIFIED` and a deterministic evaluator.

- [ ] **Step 1: Write the failing tests**

```python
from runtime.bob_verification import VerificationState, evaluate_verification


def test_no_run_is_not_triggered():
    result = evaluate_verification("abc", None)
    assert result.state is VerificationState.NOT_TRIGGERED


def test_running_run_is_running():
    result = evaluate_verification("abc", {"status": "in_progress", "sha": "abc"})
    assert result.state is VerificationState.RUNNING


def test_failed_run_is_failed():
    result = evaluate_verification("abc", {"status": "completed", "conclusion": "failure", "sha": "abc"})
    assert result.state is VerificationState.FAILED


def test_success_requires_exact_sha():
    assert evaluate_verification("abc", {"status": "completed", "conclusion": "success", "sha": "abc"}).state is VerificationState.VERIFIED
    assert evaluate_verification("abc", {"status": "completed", "conclusion": "success", "sha": "old"}).state is VerificationState.NOT_TRIGGERED
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `pytest tests/test_bob_verification.py -q`
Expected: import failure because `runtime.bob_verification` does not yet exist.

- [ ] **Step 3: Implement the minimal deterministic evaluator**

```python
from dataclasses import dataclass
from enum import Enum

class VerificationState(str, Enum):
    NOT_TRIGGERED = "NOT_TRIGGERED"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    VERIFIED = "VERIFIED"

@dataclass(frozen=True)
class VerificationResult:
    state: VerificationState

def evaluate_verification(expected_sha: str, run: dict | None) -> VerificationResult:
    if run is None or run.get("sha") != expected_sha:
        return VerificationResult(VerificationState.NOT_TRIGGERED)
    if run.get("status") != "completed":
        return VerificationResult(VerificationState.RUNNING)
    if run.get("conclusion") == "success":
        return VerificationResult(VerificationState.VERIFIED)
    return VerificationResult(VerificationState.FAILED)
```

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_bob_verification.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/bob_verification.py tests/test_bob_verification.py
git commit -m "feat: add exact-sha verification state"
```

---

### Task 2: Integrate learning with watchdog escalation

**Files:**
- Modify: `runtime/bob_watchdog.py`
- Modify: `runtime/bob_learning.py`
- Test: `tests/test_bob_watchdog.py`

**Interfaces:**
- Consumes: `LearningLedger`, `FailureLesson`, existing `PersistentSupervisor` and `BoundedWatchdog` decisions.
- Produces: deterministic escalation when the same failure class recurs after a recorded lesson.

- [ ] **Step 1: Add a failing regression test**

```python
def test_known_failure_class_escalates(tmp_path):
    ledger = LearningLedger(tmp_path / "lessons.json")
    supervisor = PersistentSupervisor("pc-1", tmp_path / "state.json")
    supervisor.heartbeat(now=100.0)
    watchdog = BoundedWatchdog(supervisor, learning_ledger=ledger, max_restarts=3, cooldown_seconds=0)
    first = watchdog.act(now=200.0, restart=lambda: (_ for _ in ()).throw(RuntimeError("crash")))
    second = watchdog.inspect(now=300.0)
    assert first.action == "escalate"
    assert second.action == "escalate"
```

- [ ] **Step 2: Run the focused regression test and verify the current behavior fails**

Run: `pytest tests/test_bob_watchdog.py::test_known_failure_class_escalates -q`
Expected: FAIL until the watchdog records and consults the ledger on the failure path.

- [ ] **Step 3: Implement the smallest integration**

The failure handler must record a `FailureLesson` with failure class `heartbeat_timeout` and consult `ledger.should_escalate("heartbeat_timeout")` before allowing another automatic restart.

- [ ] **Step 4: Run the entire watchdog test file**

Run: `pytest tests/test_bob_watchdog.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/bob_watchdog.py runtime/bob_learning.py tests/test_bob_watchdog.py
git commit -m "feat: escalate repeated watchdog failures"
```

---

### Task 3: Add a bounded task lifecycle

**Files:**
- Create: `runtime/bob_tasks.py`
- Test: `tests/test_bob_tasks.py`

**Interfaces:**
- Consumes: task identifiers and verification results.
- Produces: lifecycle states `QUEUED`, `RUNNING`, `VERIFYING`, `COMPLETED`, `FAILED`, `ESCALATED`.

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_task_lifecycle_completes_after_verified_result():
    task = Task("t1")
    assert task.state is TaskState.QUEUED
    task.start()
    task.begin_verification()
    task.complete(verified=True)
    assert task.state is TaskState.COMPLETED


def test_task_cannot_complete_without_verification():
    task = Task("t1")
    task.start()
    with pytest.raises(ValueError):
        task.complete(verified=False)
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `pytest tests/test_bob_tasks.py -q`
Expected: import failure because the task lifecycle module does not yet exist.

- [ ] **Step 3: Implement the state machine**

Reject invalid transitions and require a successful verification result before `COMPLETED`.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_bob_tasks.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/bob_tasks.py tests/test_bob_tasks.py
git commit -m "feat: add bounded BOB task lifecycle"
```

---

### Task 4: Add CI-health regression coverage

**Files:**
- Create: `tests/test_ci_verification_contract.py`
- Modify: `.github/workflows/runtime-integration.yml`
- Modify: `.github/workflows/progress-check.yml`

**Interfaces:**
- Consumes: workflow trigger definitions and verification contract.
- Produces: repository-level tests that prevent a branch from being reported as verified when no matching workflow run can exist.

- [ ] **Step 1: Add a regression test for the BOB branch trigger**

```python
def test_runtime_integration_triggers_bob_branches():
    workflow = Path(".github/workflows/runtime-integration.yml").read_text(encoding="utf-8")
    assert "bob/**" in workflow
```

- [ ] **Step 2: Run the test against the current repository**

Run: `pytest tests/test_ci_verification_contract.py -q`
Expected: PASS only when the runtime integration workflow explicitly includes BOB branches.

- [ ] **Step 3: Validate YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/runtime-integration.yml', encoding='utf-8'))"`
Expected: successful parse.

- [ ] **Step 4: Run the repository test suite**

Run: `pytest -q`
Expected: no new failures introduced by the CI contract change.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/runtime-integration.yml .github/workflows/progress-check.yml tests/test_ci_verification_contract.py
git commit -m "test: enforce CI verification contract"
```

---

### Task 5: Produce BOB control-plane operational documentation

**Files:**
- Create: `docs/BOB-CONTROL-PLANE.md`
- Test: `tests/test_bob_docs_contract.py`

**Interfaces:**
- Consumes: verification and lifecycle contracts from Tasks 1–4.
- Produces: operator-facing state definitions, escalation behavior and safe-stop rules.

- [ ] **Step 1: Write documentation contract tests**

```python
def test_bob_docs_contains_non_negotiable_states():
    text = Path("docs/BOB-CONTROL-PLANE.md").read_text(encoding="utf-8")
    for state in ("NOT_TRIGGERED", "RUNNING", "FAILED", "VERIFIED", "ESCALATED"):
        assert state in text
```

- [ ] **Step 2: Run and verify failure before documentation exists**

Run: `pytest tests/test_bob_docs_contract.py -q`
Expected: FAIL because the document does not exist.

- [ ] **Step 3: Write the operational document**

Document exact verification states, failure-learning flow, restart bounds, escalation rules, safe-stop conditions, and the rule that routine work does not require human approval.

- [ ] **Step 4: Run the documentation contract test**

Run: `pytest tests/test_bob_docs_contract.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/BOB-CONTROL-PLANE.md tests/test_bob_docs_contract.py
git commit -m "docs: define BOB control-plane contract"
```

---

## Completion Gate

The BOB control plane is not complete until all focused tests pass, the repository suite passes, the workflow trigger is present, and an actual GitHub Actions run for the exact final commit reports success. No status other than `VERIFIED` may be reported as verified.
