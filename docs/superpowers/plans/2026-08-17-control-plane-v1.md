# PROJECT-NAS Control Plane v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement four bounded, read-only Control Plane tools behind the existing Tool Gateway: `status.health`, `status.progress`, `prompt.get`, and `memory.read`, while preserving the current security boundary and 59-test regression baseline.

**Architecture:** Extend the existing `runtime/tool_gateway.py` registry with four concrete read-only tools. Keep data access in small adapters/helpers in the existing runtime modules, expose the tools only through the existing `/tools/{tool_name}` endpoint, and use strict validators plus bounded outputs. Health is an aggregate read-only probe; prompt and memory tools return structured bounded data; repository progress remains the existing bounded Git reader.

**Tech Stack:** Python 3.13, FastAPI, Flask, SQLite, existing PROJECT-NAS runtime modules, pytest, Git.

## Global Constraints

- Keep `memory`, `prompt`, and `status` as the only default namespaces.
- Preserve denial of `EXECUTE_PROCESS` and `NETWORK_ACCESS` capabilities.
- Preserve default denial of `WRITE_REPOSITORY` without explicit approval.
- Validate payloads before invoking handlers.
- Bound every externally supplied count, query, and content length.
- Keep tool execution timeouts finite.
- Record allow/deny decisions in the existing audit log.
- Health and read operations must not mutate project or memory state.
- Never expose full database contents when a bounded result is sufficient.
- No cloud AI dependencies, paid API/token dependencies, arbitrary shell execution, autonomous repository modification, network tools, vector-database migration, fabricated similarity scores, or UI work.

---

### Task 1: Add reusable bounded validators and control-plane test fixtures

**Files:**
- Modify: `runtime/tool_gateway.py`
- Test: `tests/test_tool_gateway.py`

**Interfaces:**
- Add private validators for progress, prompt, and memory payloads.
- Validators return normalized dictionaries and raise `ValueError` before handlers execute.
- Preserve the existing `ToolSpec`, `ToolGateway.execute`, audit, timeout, and namespace contracts.

- [ ] **Step 1: Write failing validator tests**

Add tests covering:

```python
def test_memory_limit_defaults_and_bounds():
    gateway = build_default_gateway(...)
    assert gateway.execute("memory.read", {})["count"] >= 0


def test_memory_limit_above_maximum_is_rejected():
    with pytest.raises(ValueError, match="limit"):
        gateway.execute("memory.read", {"limit": 51})


def test_memory_query_must_be_string():
    with pytest.raises(ValueError, match="query"):
        gateway.execute("memory.read", {"query": 123})
```

Also test unknown fields, boolean-as-integer rejection, negative/zero limits, and oversized prompt limits. Use injected handlers/fixtures so validation is tested without touching real services.

- [ ] **Step 2: Run the focused tests and verify the new tests fail**

Run:

```bash
python -m pytest -q tests/test_tool_gateway.py
```

Expected: existing tests pass and the newly added control-plane tests fail because the four tools/validators are not yet implemented.

- [ ] **Step 3: Implement minimal validators**

Use bounded constants in `tool_gateway.py`:

```python
MAX_MEMORY_LIMIT = 20
MAX_MEMORY_QUERY_CHARS = 500
MAX_PROMPT_CHARS = 12000
MAX_PROMPT_RESPONSE_CHARS = 12000
MAX_PROGRESS_COMMITS = 50
```

Normalize omitted memory limit to `5`, omitted query to `None`, and omitted prompt response bound to the configured default. Reject unsupported fields and non-string queries/content limits.

- [ ] **Step 4: Run focused tests**

Run:

```bash
python -m pytest -q tests/test_tool_gateway.py
```

Expected: validator tests pass; tool registration/execution tests for the four tools remain pending until later tasks.

- [ ] **Step 5: Commit**

```bash
git add runtime/tool_gateway.py tests/test_tool_gateway.py
git commit -m "test: define control plane input contracts"
```

---

### Task 2: Implement `memory.read`

**Files:**
- Modify: `runtime/memory_injector.py`
- Modify: `runtime/tool_gateway.py`
- Test: `tests/test_tool_gateway.py`

**Interfaces:**
- Add a bounded memory reader callable from the gateway.
- The callable accepts `query: str | None` and `limit: int` and returns:

```python
{
    "memories": [
        {"id": str, "document": str, "metadata": dict}
    ],
    "count": int,
}
```

- Recent mode uses deterministic newest-first records.
- Query mode uses the existing SQLite deterministic retrieval logic.
- No synthetic similarity scores.

- [ ] **Step 1: Add failing tests for recent memory retrieval**

Create an isolated SQLite fixture with three records and assert `{}` and `{ "limit": 2 }` return at most two actual records, newest first, with IDs/documents/metadata.

- [ ] **Step 2: Add failing tests for query retrieval and empty results**

Assert `{ "query": "runtime" }` returns only relevant stored records and a nonexistent query returns `{"memories": [], "count": 0}`.

- [ ] **Step 3: Implement the read adapter**

Expose a small function that reads from the active SQLite memory backend without mutating it. Preserve metadata JSON where present; invalid/empty metadata becomes `{}`. Reuse the existing token/retrieval behavior rather than inventing a second ranking algorithm.

- [ ] **Step 4: Register `memory.read`**

Register it with:

```python
ToolSpec(
    name="memory.read",
    capability=Capability.READ_RUNTIME,
    risk=RiskLevel.LOW,
    input_validator=_validate_memory,
    handler=...
)
```

Set a finite timeout appropriate for local SQLite access.

- [ ] **Step 5: Run focused tests**

```bash
python -m pytest -q tests/test_tool_gateway.py
```

Expected: all memory tests pass and the existing gateway security tests remain green.

- [ ] **Step 6: Commit**

```bash
git add runtime/memory_injector.py runtime/tool_gateway.py tests/test_tool_gateway.py
git commit -m "feat: add bounded memory read control tool"
```

---

### Task 3: Implement `prompt.get`

**Files:**
- Modify: `runtime/backend.py`
- Modify: `runtime/tool_gateway.py`
- Test: `tests/test_tool_gateway.py`

**Interfaces:**
- Add a prompt reader returning:

```python
{
    "path": str | None,
    "content": str,
    "chars": int,
    "truncated": bool,
}
```

- Prefer `ai/MASTER_PROMPT.md`; preserve `ai/AI_OPERATING_SYSTEM_SUMMARY.md` as fallback.
- Bound returned content and explicitly report truncation.

- [ ] **Step 1: Write failing prompt tests**

Test canonical-path selection, fallback selection, missing prompt behavior, exact `chars`, and truncation when content exceeds the configured maximum.

- [ ] **Step 2: Run focused tests and confirm failure**

```bash
python -m pytest -q tests/test_tool_gateway.py -k prompt
```

Expected: FAIL because `prompt.get` is not registered.

- [ ] **Step 3: Implement bounded prompt reader**

Reuse `PROMPT_PATHS` and `load_prompt()`. Add a bounded maximum and return metadata rather than raw unbounded content.

- [ ] **Step 4: Register `prompt.get`**

Use `Capability.READ_RUNTIME`, `RiskLevel.LOW`, strict empty-payload validation, and a finite timeout.

- [ ] **Step 5: Run focused tests**

```bash
python -m pytest -q tests/test_tool_gateway.py -k prompt
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add runtime/backend.py runtime/tool_gateway.py tests/test_tool_gateway.py
git commit -m "feat: add bounded prompt control tool"
```

---

### Task 4: Implement `status.health`

**Files:**
- Modify: `runtime/backend.py`
- Modify: `runtime/tool_gateway.py`
- Test: `tests/test_tool_gateway.py`

**Interfaces:**
- Add a deterministic health handler returning:

```python
{
    "status": "healthy" | "degraded" | "unavailable",
    "components": {
        "ollama": {...},
        "memory_api": {...},
        "memory_sqlite": {...},
        "repository": {...},
        "model": {...},
    },
}
```

- Health probes are bounded, local, and read-only.
- Required/core failures produce `unavailable`; non-core failures produce `degraded`; all required checks passing produces `healthy`.

- [ ] **Step 1: Write failing health-state tests**

Inject probe functions and test:

```python
def test_health_is_healthy_when_all_probes_pass(): ...
def test_health_is_degraded_when_optional_dependency_fails(): ...
def test_health_is_unavailable_when_core_runtime_fails(): ...
```

Also assert the result contains explicit component failure information and no memory contents.

- [ ] **Step 2: Add non-mutating probes**

Use bounded loopback HTTP checks for Ollama/Memory API, SQLite read-only connectivity/count, repository readability, and configured model availability. Do not start/stop services or create records from health.

- [ ] **Step 3: Implement aggregate-state logic**

Use explicit component criticality rather than deriving state from an undifferentiated boolean. A core runtime failure maps to `unavailable`; otherwise any failed non-core component maps to `degraded`.

- [ ] **Step 4: Register `status.health`**

Use `Capability.READ_RUNTIME`, `RiskLevel.LOW`, empty-object validation, and a finite timeout.

- [ ] **Step 5: Run focused health tests**

```bash
python -m pytest -q tests/test_tool_gateway.py -k health
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add runtime/backend.py runtime/tool_gateway.py tests/test_tool_gateway.py
git commit -m "feat: add runtime health control tool"
```

---

### Task 5: Verify the complete gateway contract and HTTP boundary

**Files:**
- Modify: `tests/test_tool_gateway.py`
- Create or modify: `tests/test_backend.py`

**Interfaces:**
- Keep `/tools/{tool_name}` as the only transport boundary for control-plane tools.
- Preserve HTTP semantics: 404 unknown, 403 policy denial, 400 validation failure, 504 timeout.

- [ ] **Step 1: Add registration tests for all four tools**

Assert `build_default_gateway()` contains exactly the intended four control-plane tools and `status.progress` remains bounded to `1..50` commits.

- [ ] **Step 2: Add security regression tests**

Assert non-allowlisted namespaces are denied before validators/handlers; process/network/write capabilities remain denied; audit entries are present for both allow and deny decisions.

- [ ] **Step 3: Add FastAPI endpoint tests**

Exercise `/tools/status.health`, `/tools/status.progress`, `/tools/prompt.get`, and `/tools/memory.read`, plus the 404/403/400/504 error paths using dependency injection/mocks where external services are involved.

- [ ] **Step 4: Run the gateway and backend suites**

```bash
python -m pytest -q tests/test_tool_gateway.py tests/test_backend.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_tool_gateway.py tests/test_backend.py
 git commit -m "test: verify control plane API boundary"
```

---

### Task 6: Full regression and runtime smoke verification

**Files:**
- No source changes expected.

**Interfaces:**
- Verification only. Do not weaken tests or security constraints to make failures disappear.

- [ ] **Step 1: Run complete regression**

```bash
python -m pytest -q
```

Expected: all tests pass, including the original 59-test baseline plus the new control-plane coverage.

- [ ] **Step 2: Check repository formatting/diff hygiene**

```bash
git diff --check
git status --short
git log --oneline -8
```

Expected: no whitespace errors and only intentional tracked changes.

- [ ] **Step 3: Verify local runtime endpoints**

```bash
curl -fsS http://127.0.0.1:5000/health
curl -fsS http://127.0.0.1:11434/api/tags
```

Expected: both local services respond successfully.

- [ ] **Step 4: Verify the four control-plane tools through HTTP**

```bash
curl -fsS -X POST http://127.0.0.1:5000/tools/status.health -H 'Content-Type: application/json' -d '{}'
curl -fsS -X POST http://127.0.0.1:5000/tools/status.progress -H 'Content-Type: application/json' -d '{"commits":5}'
curl -fsS -X POST http://127.0.0.1:5000/tools/prompt.get -H 'Content-Type: application/json' -d '{}'
curl -fsS -X POST http://127.0.0.1:5000/tools/memory.read -H 'Content-Type: application/json' -d '{"limit":5}'
```

Expected: each returns structured JSON without exposing unbounded state.

- [ ] **Step 5: Re-run explicit memory persistence proof**

Send one unique `Remember that ...` probe through `/chat`, then query SQLite for the unique probe and assert exactly one matching record. This confirms the control-plane work did not regress the already-proven explicit persistence contract.

- [ ] **Step 6: Final commit/tag state review**

```bash
git diff --check
git status --short
git log --oneline -10
```

If all checks pass, create the final implementation commit only for any remaining intentional changes and report exact test counts and commit SHAs.

---

## Plan Self-Review

- **Spec coverage:** All four tools, bounded inputs/outputs, health state semantics, security constraints, API integration, audit logging, timeouts, and regression coverage are mapped to Tasks 1–6.
- **Placeholder scan:** No `TBD`, `TODO`, or unspecified implementation step is required.
- **Type consistency:** Tool handlers return dictionaries; validators return normalized dictionaries; gateway registration uses existing `ToolSpec`/`Capability`/`RiskLevel` interfaces.
- **Scope:** One cohesive control-plane subsystem; no UI, cloud, arbitrary execution, or unrelated refactor work.
