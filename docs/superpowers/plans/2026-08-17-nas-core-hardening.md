# PROJECT-NAS Core Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden PROJECT-NAS into a zero-cost local-first runtime with one governed tool boundary, deterministic policy, resilient memory/AI routing, safe lifecycle control, and complete regression coverage.

**Architecture:** Keep the existing runtime structure and add focused orchestration, AI-routing, memory, and audit modules rather than rewriting stable components. Route agent actions through `ToolGateway`, keep FastAPI/Flask layers as adapters, and preserve SQLite as the guaranteed fallback while Ollama/ChromaDB remain optional local accelerators.

**Tech Stack:** Python 3.12+, FastAPI, Flask, SQLite, optional ChromaDB, Ollama, Bash, pytest.

## Global Constraints

- No required paid cloud AI/API subscription or token-credit dependency.
- Local/self-hosted/open-source services are the default.
- Practical limits are user hardware, storage, installed models, and local runtime availability.
- Process execution and arbitrary network access remain denied by default.
- Repository writes require explicit approval.
- High/critical-risk actions require explicit approval.
- Input validation occurs before handler execution.
- Every tool has a finite timeout and bounded audit history.
- SQLite is the guaranteed memory fallback; ChromaDB is optional.
- Prompt, context, memory, and response sizes remain bounded.
- Preserve the existing 59-test baseline while expanding contract coverage.

---

### Task 1: Establish audit and execution contracts

**Files:**
- Create: `runtime/audit.py`
- Modify: `runtime/tool_gateway.py`
- Test: `tests/test_tool_gateway.py`

**Interfaces:**
- `AuditEvent(tool: str, allowed: bool, reason: str)` immutable record.
- `AuditLog(limit: int = 100).record(tool: str, allowed: bool, reason: str) -> None`.
- `AuditLog.snapshot() -> list[dict[str, object]]`.
- `ToolGateway.audit_log` remains backwards-compatible as a list-like public audit surface.

- [ ] **Step 1: Write failing audit tests**

```python
def test_audit_log_is_bounded_and_keeps_latest_events():
    log = AuditLog(limit=2)
    log.record("a", True, "ok")
    log.record("b", False, "denied")
    log.record("c", True, "ok")
    assert [event["tool"] for event in log.snapshot()] == ["b", "c"]
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python -m pytest tests/test_tool_gateway.py -q`
Expected: FAIL because `runtime.audit` does not yet provide `AuditLog`.

- [ ] **Step 3: Implement `runtime/audit.py` and integrate the gateway**

Keep the gateway's existing policy/timeout behavior intact; replace only the audit storage implementation and expose a snapshot compatible with current tests.

- [ ] **Step 4: Run focused gateway tests**

Run: `python -m pytest tests/test_tool_gateway.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/audit.py runtime/tool_gateway.py tests/test_tool_gateway.py
git commit -m "feat: centralize bounded runtime audit logging"
```

### Task 2: Expand governed read capabilities

**Files:**
- Modify: `runtime/tool_gateway.py`
- Modify: `runtime/backend.py`
- Test: `tests/test_tool_gateway.py`
- Test: `tests/test_backend.py`

**Interfaces:**
- `prompt.get` returns `{"path": str | None, "prompt": str}`.
- `status.health` returns deterministic local runtime health metadata without invoking external commands.
- `memory.read` accepts `{"query": str, "limit": int}` with strict bounds and returns bounded memory records.

- [ ] **Step 1: Add failing tests for `prompt.get`, `status.health`, and `memory.read`**

```python
def test_prompt_get_is_allowlisted():
    gateway = build_default_gateway()
    result = gateway.execute("prompt.get", {})
    assert "prompt" in result


def test_unknown_payload_keys_are_rejected_for_memory_read():
    gateway = build_default_gateway()
    with pytest.raises(ValueError):
        gateway.execute("memory.read", {"query": "x", "limit": 2, "extra": True})
```

- [ ] **Step 2: Run focused tests and verify the new tests fail**

Run: `python -m pytest tests/test_tool_gateway.py tests/test_backend.py -q`
Expected: FAIL for the unregistered tools.

- [ ] **Step 3: Implement validators and bounded read handlers**

Use dependency injection for prompt and memory handlers. Do not import the FastAPI app from the gateway to avoid circular dependencies.

- [ ] **Step 4: Run the focused suite**

Run: `python -m pytest tests/test_tool_gateway.py tests/test_backend.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/tool_gateway.py runtime/backend.py tests/test_tool_gateway.py tests/test_backend.py
git commit -m "feat: add governed runtime read capabilities"
```

### Task 3: Introduce the memory abstraction and fallback

**Files:**
- Create: `runtime/memory.py`
- Modify: `runtime/memory_injector.py`
- Test: `tests/test_memory.py`

**Interfaces:**
- `MemoryStore.read(query: str, limit: int = 2) -> list[dict[str, object]]`.
- `MemoryStore.write(document: str, metadata: dict[str, object] | None = None) -> str`.
- `SQLiteMemoryStore` implements the interface using the existing schema/retrieval semantics.
- `ChromaMemoryStore` is optional and selected only when ChromaDB is importable and configured.
- `build_memory_store(path: str, prefer_chroma: bool = True) -> MemoryStore` never requires ChromaDB.

- [ ] **Step 1: Add failing SQLite contract tests**

```python
def test_sqlite_memory_round_trip(tmp_path):
    store = SQLiteMemoryStore(str(tmp_path / "memory.sqlite3"))
    memory_id = store.write("PROJECT-NAS local-first runtime", {"kind": "decision"})
    rows = store.read("local-first runtime", limit=1)
    assert rows[0]["id"] == memory_id
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python -m pytest tests/test_memory.py -q`
Expected: FAIL because `runtime.memory` does not exist.

- [ ] **Step 3: Extract/reuse the existing bounded SQLite retrieval behavior**

Do not change the current memory database location contract or environment variable names. Preserve `PROJECT_NAS_MEMORY_DB`, memory/context/response bounds, and explicit persistence semantics.

- [ ] **Step 4: Add fallback tests with Chroma unavailable**

```python
def test_memory_factory_does_not_require_chromadb(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "chromadb", None)
    store = build_memory_store(str(tmp_path / "memory"))
    assert isinstance(store, SQLiteMemoryStore)
```

- [ ] **Step 5: Run memory tests**

Run: `python -m pytest tests/test_memory.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add runtime/memory.py runtime/memory_injector.py tests/test_memory.py
git commit -m "feat: unify SQLite and optional vector memory"
```

### Task 4: Add local AI routing and fallback

**Files:**
- Create: `runtime/ai_router.py`
- Test: `tests/test_ai_router.py`

**Interfaces:**
- `LocalModel(model: str, available: bool)` immutable metadata.
- `AIRouter(preferred_model: str, model_lister: Callable[[], list[str]], generator: Callable[..., dict])`.
- `AIRouter.generate(prompt: str, context: str = "") -> dict[str, object]`.
- Prompt/context are bounded before the generator is called.

- [ ] **Step 1: Add failing tests for preferred-model selection and fallback**

```python
def test_router_falls_back_when_preferred_model_is_missing():
    calls = []
    router = AIRouter("preferred", lambda: ["fallback"], fake_generator(calls))
    result = router.generate("hello")
    assert result["model"] == "fallback"
    assert calls[-1]["model"] == "fallback"
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `python -m pytest tests/test_ai_router.py -q`
Expected: FAIL because the router is not implemented.

- [ ] **Step 3: Implement bounded Ollama routing**

Use the existing local Ollama URL/model environment contracts. No cloud fallback. If no local model is available, return a deterministic structured failure rather than silently switching to a paid service.

- [ ] **Step 4: Add timeout and oversized-input tests**

Verify the router never passes more than the configured prompt/context limits to the generator and surfaces timeout failures predictably.

- [ ] **Step 5: Run router tests**

Run: `python -m pytest tests/test_ai_router.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add runtime/ai_router.py tests/test_ai_router.py
git commit -m "feat: add zero-cost local model routing and fallback"
```

### Task 5: Add the orchestrator and verification boundary

**Files:**
- Create: `runtime/orchestrator.py`
- Modify: `runtime/tool_gateway.py`
- Test: `tests/test_orchestrator.py`

**Interfaces:**
- `ExecutionPlan(intent: str, tool_name: str | None, payload: dict)` immutable.
- `Orchestrator(gateway: ToolGateway, verifier: Callable[[object], bool] | None = None)`.
- `Orchestrator.execute(plan: ExecutionPlan) -> dict[str, object]`.

- [ ] **Step 1: Write failing tests for governed execution and verification**

```python
def test_orchestrator_never_executes_without_gateway_approval():
    gateway = build_default_gateway()
    orchestrator = Orchestrator(gateway)
    with pytest.raises(PermissionError):
        orchestrator.execute(ExecutionPlan("run shell", "shell.run", {}))
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `python -m pytest tests/test_orchestrator.py -q`
Expected: FAIL because the orchestrator is not implemented.

- [ ] **Step 3: Implement plan execution through `ToolGateway.execute()` only**

The orchestrator must not call subprocesses, HTTP clients, repository writers, or model generators directly. Verification failure must return a structured failed result and never report success.

- [ ] **Step 4: Add audit and failure-path assertions**

Verify denied tools are recorded by the gateway and verifier failures cannot be converted into successful responses.

- [ ] **Step 5: Run orchestrator tests**

Run: `python -m pytest tests/test_orchestrator.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add runtime/orchestrator.py runtime/tool_gateway.py tests/test_orchestrator.py
git commit -m "feat: add governed execution orchestrator"
```

### Task 6: Remove backend side doors and wire governed services

**Files:**
- Modify: `runtime/backend.py`
- Modify: `runtime/tool_gateway.py`
- Test: `tests/test_backend.py`

**Interfaces:**
- FastAPI endpoints delegate governed agent actions to the gateway/orchestrator.
- TODO persistence remains available only through explicitly defined backend CRUD semantics; it must not be exposed as an implicit agent capability.

- [ ] **Step 1: Add tests proving agent tool access cannot reach raw TODO writes**

```python
def test_tool_gateway_has_no_todo_write_capability():
    gateway = build_default_gateway()
    with pytest.raises(PermissionError):
        gateway.execute("todo.create", {"id": "x", "title": "bypass"})
```

- [ ] **Step 2: Run backend/gateway tests**

Run: `python -m pytest tests/test_backend.py tests/test_tool_gateway.py -q`
Expected: PASS after the contract is explicit.

- [ ] **Step 3: Wire prompt/progress/health through governed read handlers**

Keep compatibility for existing HTTP clients while ensuring tool execution has one policy boundary.

- [ ] **Step 4: Add API status-code tests for 400/403/404/504**

Confirm validator, policy, missing-tool, and timeout errors map to the existing FastAPI error contract.

- [ ] **Step 5: Commit**

```bash
git add runtime/backend.py runtime/tool_gateway.py tests/test_backend.py
git commit -m "fix: prevent backend agent capability bypasses"
```

### Task 7: Harden lifecycle and doctor integration

**Files:**
- Modify: `runtime/project-nas.sh`
- Modify: `runtime/doctor.py` only where required by discovered contract gaps
- Test: `tests/test_runtime_controller.py`

**Interfaces:**
- `start`, `stop`, `restart`, `status`, `doctor`, `chat` remain stable CLI commands.
- Controller-owned processes can be stopped only when PID and recorded process identity both match.
- Externally managed services are never killed by `stop`.

- [ ] **Step 1: Add tests for stale PID, mismatched identity, and partial ownership state**

```python
def test_stop_refuses_mismatched_identity(tmp_path):
    # create PID/identity state that points at a live unrelated process
    # assert non-zero exit and explicit ownership error
    ...
```

- [ ] **Step 2: Run lifecycle tests**

Run: `python -m pytest tests/test_runtime_controller.py -q`
Expected: the new ownership cases fail before the hardening change.

- [ ] **Step 3: Implement only the minimum lifecycle changes**

Preserve the already-working ownership semantics and external-service behavior from commits `a37cfca`, `81def16`, and `af2d81d`.

- [ ] **Step 4: Run lifecycle tests and shell syntax validation**

Run: `python -m pytest tests/test_runtime_controller.py -q && bash -n runtime/project-nas.sh`
Expected: PASS and exit 0.

- [ ] **Step 5: Commit**

```bash
git add runtime/project-nas.sh runtime/doctor.py tests/test_runtime_controller.py
git commit -m "test: close remaining runtime lifecycle gaps"
```

### Task 8: Full regression, security contract, and documentation verification

**Files:**
- Modify: `tests/` only for missing regression coverage discovered in Tasks 1-7.
- Modify: `docs/` only where runtime behavior documentation is stale.

- [ ] **Step 1: Run the complete test suite**

Run: `python -m pytest -q`
Expected: all tests pass, including the original 59-test baseline.

- [ ] **Step 2: Run static/syntax checks**

Run: `python -m compileall -q runtime tests && bash -n runtime/project-nas.sh && git diff --check`
Expected: exit 0 with no whitespace errors.

- [ ] **Step 3: Run runtime diagnostics**

Run: `python runtime/doctor.py`
Expected: diagnostics correctly distinguish optional dependencies, local model availability, database state, and service reachability without false positives.

- [ ] **Step 4: Verify the lifecycle commands in a controlled environment**

Run: `runtime/project-nas.sh status`
Then, only if the environment has a safe local runtime available, run `start`, `status`, `doctor`, and `stop` and confirm externally managed services are preserved.

- [ ] **Step 5: Review the final diff for security bypasses**

Search: `grep -RniE 'subprocess|os\.system|requests\.|urllib|curl|ollama' runtime` and inspect every newly introduced call for gateway/policy ownership.

- [ ] **Step 6: Commit final regression/docs changes**

```bash
git add tests docs
git commit -m "test: verify PROJECT-NAS core hardening"
```

- [ ] **Step 7: Open a pull request for review**

```bash
git push -u origin feat/nas-core-hardening
```

Create a PR into `main` with the test results and explicit note that the architecture remains zero-cost and local-first.
