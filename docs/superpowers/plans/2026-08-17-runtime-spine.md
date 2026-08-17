# Runtime Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the FastAPI backend the single local control-plane entry point for PROJECT-NAS chat while preserving the existing bounded memory/LLM worker and security contracts.

**Architecture:** Add a thin FastAPI `/chat` orchestration boundary that validates requests, enforces a loopback-only worker URL, calls the existing Flask memory/LLM worker, and normalizes worker responses/errors. Keep the current tool gateway, policy engine, memory implementation, and runtime controller intact unless tests expose a concrete contract gap.

**Tech Stack:** Python 3.12+, FastAPI, Flask, requests, pytest, SQLite, Ollama, Bash.

## Global Constraints

- Local-first: no mandatory paid cloud AI/API subscription.
- Loopback-only LLM worker communication.
- Process execution, arbitrary network access, and repository writes remain denied by default.
- Prompt, context, response, memory, and tool inputs remain explicitly bounded.
- Existing controller ownership protections must not regress.
- Existing tests must remain green.

---

### Task 1: Lock the backend chat contract

**Files:**
- Modify: `runtime/backend.py`
- Test: `tests/test_backend.py`

**Interfaces:**
- Consumes: `PROJECT_NAS_MEMORY_HEALTH_URL` as the existing local worker endpoint configuration; existing `requests` dependency.
- Produces: `POST /chat` returning JSON with `response` and optional `model`, `budget`, and `memory` metadata.

- [ ] **Step 1: Write failing endpoint tests**

```python
def test_chat_rejects_missing_prompt(client):
    response = client.post("/chat", json={})
    assert response.status_code == 400


def test_chat_rejects_oversized_prompt(client):
    response = client.post("/chat", json={"prompt": "x" * 12001})
    assert response.status_code == 413
```

- [ ] **Step 2: Run the focused tests**

Run: `python -m pytest -q tests/test_backend.py -k chat`
Expected: FAIL because `/chat` does not yet exist.

- [ ] **Step 3: Implement the bounded request model and worker call**

Add constants for the worker request limits and implement a `/chat` endpoint that:
1. requires a JSON object;
2. requires a non-empty string `prompt`;
3. accepts optional string `context`;
4. rejects values over the existing prompt/context limits;
5. reads the worker URL from `PROJECT_NAS_MEMORY_HEALTH_URL` only when it is explicitly configured as a `/chat` endpoint, otherwise derives `/chat` from the configured memory health base URL;
6. rejects non-loopback worker hosts using the same URL policy as `memory_injector.py`;
7. POSTs JSON `{context, prompt}` to the worker;
8. returns the worker response without leaking arbitrary upstream payloads.

- [ ] **Step 4: Add deterministic upstream error mapping**

Map connection/timeout errors to 503, invalid worker JSON or missing `response` to 502, and worker 4xx/5xx failures to 502 unless the failure is clearly a local validation error.

- [ ] **Step 5: Run focused tests**

Run: `python -m pytest -q tests/test_backend.py -k chat`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add runtime/backend.py tests/test_backend.py
git commit -m "feat: expose unified local chat endpoint"
```

### Task 2: Prove loopback and payload boundaries

**Files:**
- Modify: `runtime/backend.py`
- Test: `tests/test_backend.py`

**Interfaces:**
- Consumes: `/chat` contract from Task 1.
- Produces: deterministic rejection of remote worker URLs and malformed upstream responses.

- [ ] **Step 1: Add failing security tests**

```python
def test_chat_rejects_remote_worker(monkeypatch, client):
    monkeypatch.setenv("PROJECT_NAS_CHAT_WORKER_URL", "https://example.com/chat")
    response = client.post("/chat", json={"prompt": "hello"})
    assert response.status_code == 503


def test_chat_rejects_invalid_worker_response(monkeypatch, client):
    # Stub the HTTP client so the worker returns JSON without a response field.
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest -q tests/test_backend.py -k "remote_worker or invalid_worker"`
Expected: FAIL before the enforcement is complete.

- [ ] **Step 3: Implement loopback validation and response sanitization**

Reuse a small backend-local helper that accepts `localhost` and loopback IP literals only. Reject DNS names other than `localhost` and reject non-http(s) schemes.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest -q tests/test_backend.py -k "chat or worker"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add runtime/backend.py tests/test_backend.py
git commit -m "security: enforce loopback chat worker"
```

### Task 3: Integrate controller chat with the control plane

**Files:**
- Modify: `runtime/project-nas.sh`
- Test: `tests/test_runtime_controller.py`

**Interfaces:**
- Consumes: FastAPI `/chat` endpoint from Task 1.
- Produces: controller `chat` command targeting the canonical backend URL.

- [ ] **Step 1: Add a failing controller configuration test**

Verify the script constructs its chat request from `PROJECT_NAS_BACKEND_URL` and does not hard-code the worker implementation endpoint.

- [ ] **Step 2: Run the focused test**

Run: `python -m pytest -q tests/test_runtime_controller.py -k chat`
Expected: FAIL until the controller is updated.

- [ ] **Step 3: Update the controller**

Introduce `BACKEND_URL` with default `http://127.0.0.1:5001` only if the backend is actually configured to run there; otherwise preserve the current runtime port and make the URL environment-driven. The controller must never kill an externally managed service.

- [ ] **Step 4: Verify shell syntax**

Run: `bash -n runtime/project-nas.sh`
Expected: exit 0.

- [ ] **Step 5: Run controller tests**

Run: `python -m pytest -q tests/test_runtime_controller.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add runtime/project-nas.sh tests/test_runtime_controller.py
git commit -m "feat: route controller chat through backend"
```

### Task 4: End-to-end regression verification

**Files:**
- Modify: `README.md` only if the documented endpoint contract differs from the implemented contract.
- Test: existing `tests/` suite.

**Interfaces:**
- Consumes: all runtime contracts from Tasks 1-3.
- Produces: verified local runtime spine.

- [ ] **Step 1: Run the full suite**

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 2: Run static/runtime checks**

Run:
```bash
bash -n runtime/project-nas.sh
python -m compileall -q runtime tests
git diff --check
python runtime/doctor.py
```
Expected: all commands exit successfully.

- [ ] **Step 3: Verify the gateway contract**

Run the gateway regression tests and confirm `status.health`, `status.progress`, `prompt.get`, and `memory.read` remain available while unknown namespaces remain denied.

- [ ] **Step 4: Verify no remote model path was introduced**

Search runtime sources for non-loopback model URLs and ensure only explicit loopback validation paths remain.

- [ ] **Step 5: Commit documentation corrections if needed**

```bash
git add README.md
git commit -m "docs: align runtime control-plane contract"
```
