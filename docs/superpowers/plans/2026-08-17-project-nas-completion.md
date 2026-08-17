# PROJECT-NAS Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the documented PROJECT-NAS v1 gaps and prove the local-first runtime is bounded, policy-gated, portable, and reproducible.

**Architecture:** Keep Flask memory/chat, FastAPI control plane, ToolGateway, PolicyEngine, and runtime controller as separate boundaries. Make the documented read-only control-plane tools real, add deterministic local model fallback and context budgeting, strengthen memory governance, and verify the whole system through tests and CI.

**Tech Stack:** Python 3.12, Flask, FastAPI, SQLite, optional ChromaDB, requests, pytest, Bash, GitHub Actions.

## Global Constraints

- Local-first and zero required paid cloud AI/API subscriptions.
- Local model endpoint must remain loopback-only by default.
- Process execution, arbitrary network access, and repository writes remain denied by default.
- Runtime state is not source code and must remain ignored.
- No completion claim without passing regression and CI.

---

### Task 1: Make the documented control plane real

**Files:**
- Modify: `runtime/tool_gateway.py`
- Modify: `runtime/backend.py`
- Modify: `tests/test_tool_gateway.py`
- Modify: `tests/test_backend.py`
- Create: `tests/test_control_plane_contract.py`

**Interfaces:**
- `status.health` consumes `health_report()` and returns its dictionary.
- `status.progress` keeps `{"commits": int}` with 1-50 bounds.
- `prompt.get` accepts optional `max_chars` from 1-12000 and returns bounded prompt metadata.
- `memory.read` accepts optional `query` string and `limit` 1-20 and returns bounded memory records.

- [ ] **Step 1: Add failing gateway registration tests**

Assert `build_default_gateway()` contains exactly the four documented read-only tools and that each validator rejects unknown fields and invalid bounds.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `pytest -q tests/test_tool_gateway.py tests/test_control_plane_contract.py`

Expected: new registration/contract tests fail because only `status.progress` is registered.

- [ ] **Step 3: Implement the four bounded read-only ToolSpecs**

Add validators for health, prompt, and memory. Import adapters lazily to avoid circular imports. Register each with `READ_RUNTIME` or `READ_REPOSITORY`, `LOW` risk, and a bounded timeout.

- [ ] **Step 4: Add FastAPI `/health` and bounded adapter endpoints**

Expose `GET /health` through `health_report()`. Route `/prompt` through `read_prompt()`, keep `/progress` gateway-backed, and keep `/tools/{tool_name}` as the canonical control-plane execution path.

- [ ] **Step 5: Run focused tests and verify pass**

Run: `pytest -q tests/test_tool_gateway.py tests/test_backend.py tests/test_control_plane_contract.py`

- [ ] **Step 6: Commit**

Run: `git add runtime/tool_gateway.py runtime/backend.py tests/test_tool_gateway.py tests/test_backend.py tests/test_control_plane_contract.py && git commit -m "feat: complete v1 control plane"`

### Task 2: Add deterministic local model discovery and fallback

**Files:**
- Modify: `runtime/memory_injector.py`
- Modify: `tests/test_chat_contract.py`
- Modify: `tests/test_chat_e2e.py`

**Interfaces:**
- `discover_local_models(base_url: str) -> list[str]`
- `select_local_model(configured: str, available: list[str]) -> str | None`
- `is_loopback_ollama_url(url: str) -> bool` remains the security gate.

- [ ] **Step 1: Add failing discovery/fallback tests**

Test configured model wins, configured model missing falls back deterministically, empty model inventory fails cleanly, malformed `/api/tags` fails closed, and remote URLs remain rejected.

- [ ] **Step 2: Implement deterministic discovery**

Query only the loopback Ollama tags endpoint. Deduplicate names and sort fallback candidates lexicographically after configured-model priority.

- [ ] **Step 3: Use selected model for `/chat` and `/health`**

Resolve the model once per request without mutating the configured environment. Return a clear 503 when no local model exists.

- [ ] **Step 4: Run chat tests**

Run: `pytest -q tests/test_chat_contract.py tests/test_chat_e2e.py tests/test_memory_injector.py`

- [ ] **Step 5: Commit**

Run: `git add runtime/memory_injector.py tests/test_chat_contract.py tests/test_chat_e2e.py && git commit -m "feat: add deterministic local model fallback"`

### Task 3: Make context and memory governance explicit

**Files:**
- Modify: `runtime/memory_injector.py`
- Modify: `tests/test_memory_retrieval.py`
- Modify: `tests/test_memory_read.py`
- Modify: `tests/test_memory_injector.py`
- Create: `tests/test_memory_governance.py`

**Interfaces:**
- `build_context(static_context: str, memory_context: str, user_prompt: str) -> tuple[str, dict]`
- `redact_memory_text(text: str) -> str`
- `should_persist_memory(prompt: str) -> bool` keeps explicit-trigger semantics.

- [ ] **Step 1: Add failing budget/redaction tests**

Cover total prompt budget, deterministic truncation, secret/token redaction, response bounds, and ordinary-chat non-persistence.

- [ ] **Step 2: Implement deterministic context budgeting**

Reserve system/runtime facts and the full user prompt first. Allocate the remaining budget between static context and retrieved memory with fixed caps. Return metadata describing truncation for observability.

- [ ] **Step 3: Redact before persistence**

Mask common API-key, bearer-token, password, and private-key material before storing explicit memories. Never store raw secrets merely because the user said “remember”.

- [ ] **Step 4: Preserve SQLite/Chroma compatibility**

Apply the same logical contract to both backends and keep existing bounded read behavior.

- [ ] **Step 5: Run memory/chat regression**

Run: `pytest -q tests/test_memory_injector.py tests/test_memory_retrieval.py tests/test_memory_read.py tests/test_memory_governance.py tests/test_chat_contract.py tests/test_chat_e2e.py`

- [ ] **Step 6: Commit**

Run: `git add runtime/memory_injector.py tests/test_memory_injector.py tests/test_memory_retrieval.py tests/test_memory_read.py tests/test_memory_governance.py tests/test_chat_contract.py tests/test_chat_e2e.py && git commit -m "feat: enforce context and memory governance"`

### Task 4: Harden runtime controller lifecycle

**Files:**
- Modify: `runtime/project-nas.sh`
- Modify: `tests/test_runtime_controller.py`

- [ ] **Step 1: Add lifecycle regression tests**

Cover externally-managed services, incomplete ownership state, PID identity mismatch, successful owned stop, and readiness failure cleanup.

- [ ] **Step 2: Run controller tests and verify failures where behavior is missing**

Run: `pytest -q tests/test_runtime_controller.py`

- [ ] **Step 3: Implement minimal fail-closed lifecycle fixes**

Never kill a PID unless both PID and exact captured command identity match. Remove partial ownership state after failed startup. Preserve externally managed services.

- [ ] **Step 4: Run controller tests**

Run: `pytest -q tests/test_runtime_controller.py`

- [ ] **Step 5: Commit**

Run: `git add runtime/project-nas.sh tests/test_runtime_controller.py && git commit -m "test: harden runtime controller lifecycle"`

### Task 5: Make CI and documentation match the executable contract

**Files:**
- Modify: `.github/workflows/progress-check.yml`
- Modify: `README.md`
- Modify: `ACTION-PLAN.md`
- Modify: `TRANSFER-MANIFEST.md`
- Modify: `Obsidian/01-System/Runtime.md`
- Modify: `Obsidian/04-Project/Project-Status.md`

- [ ] **Step 1: Add CI checks for the new contracts**

Keep containerized Python 3.12 execution and add the control-plane and governance tests to the required suite. Keep doctor fail-closed.

- [ ] **Step 2: Reconcile documentation**

Document the actual four-tool gateway, model fallback, budget policy, memory redaction, and controller ownership contract. Remove claims of capabilities that do not exist.

- [ ] **Step 3: Run repository hygiene checks**

Run: `bash -n runtime/project-nas.sh && python -m compileall -q runtime tests && git diff --check`

- [ ] **Step 4: Commit**

Run: `git add .github/workflows/progress-check.yml README.md ACTION-PLAN.md TRANSFER-MANIFEST.md Obsidian/01-System/Runtime.md Obsidian/04-Project/Project-Status.md && git commit -m "docs: align runtime contracts and CI"`

### Task 6: Full verification and completion gate

**Files:**
- No source changes unless a verification failure identifies a concrete defect.

- [ ] **Step 1: Run complete local-equivalent verification**

Run:
`bash -n runtime/project-nas.sh`
`python -m compileall -q runtime tests`
`git diff --check`
`pytest -q tests`
`python runtime/doctor.py`
`python runtime/progress.py --commits 5`

- [ ] **Step 2: Inspect Git status and history**

Run: `git status --short` and `git log --oneline -10`. Confirm no runtime databases, logs, PID files, caches, or generated artifacts are tracked.

- [ ] **Step 3: Push and verify GitHub Actions**

Push the implementation branch, wait for `PROJECT-NAS Progress Check`, inspect every job step, and fix any failure rather than bypassing it.

- [ ] **Step 4: Re-run regression after CI fixes**

Run the full local suite again and require a green CI run on the final commit.

- [ ] **Step 5: Commit any final verification-only fixes**

Use a focused `fix:` or `test:` commit with the exact failing contract in the message.

- [ ] **Step 6: Final completion gate**

Only report 100% when all success criteria in `docs/superpowers/specs/2026-08-17-project-nas-completion-design.md` are satisfied and the final CI run is green.
