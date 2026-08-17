# PROJECT-NAS Runtime Spine Design

## Goal
Turn the existing local runtime into one coherent, testable control plane while preserving the $0 local-first architecture and existing security boundaries.

## Current State
The repository already has a runtime controller, FastAPI backend, Flask memory/chat service, bounded tool gateway, deterministic policy engine, SQLite/Chroma memory adapters, Ollama fallback logic, diagnostics, and regression tests. The main architectural gap is that chat orchestration remains split between `runtime/backend.py` and `runtime/memory_injector.py`, while direct TODO endpoints bypass the policy gateway.

## Design

### 1. Single local control plane
`runtime/backend.py` becomes the canonical API surface for health, prompt, progress, memory reads, chat, and task/session operations. The existing memory injector remains the local model/memory worker during this transition so the change does not require a risky rewrite of its proven retrieval/persistence logic.

### 2. Chat contract
Add `POST /chat` to the FastAPI backend. It validates bounded `prompt` and `context` inputs, forwards only to the loopback memory/chat service, returns a stable `{response, model?, memory?, budget?}` contract, and converts worker failures into deterministic HTTP errors. The public caller therefore no longer needs to know port 5000 implementation details.

### 3. Gateway contract
Keep `status.health`, `status.progress`, `prompt.get`, and `memory.read` read-only and bounded. Add a read-only `task.list` surface only if required by the existing session API. Do not enable process execution, arbitrary network access, or repository writes.

### 4. Task/TODO safety
Existing TODO HTTP endpoints remain useful but gain strict validation and a policy-backed path for future autonomous writes. No autonomous write capability is enabled in this phase; direct HTTP writes are treated as application CRUD, not privileged repository/process operations.

### 5. Runtime ownership
Preserve the controller's PID/identity ownership rules. Externally managed Ollama or memory services must never be killed by `stop`.

### 6. $0 / portability
No paid API, cloud inference, hosted vector database, or token-credit dependency is introduced. Ollama remains loopback-only. SQLite remains the guaranteed memory/session fallback; Chroma is optional.

## Error handling
- Invalid request: HTTP 400/413.
- Policy denial: HTTP 403.
- Missing tool: HTTP 404.
- Worker unavailable: HTTP 503.
- Worker/LLM upstream failure: HTTP 502.
- Tool timeout: HTTP 504.
- No endpoint exposes arbitrary shell execution or remote model URLs.

## Testing
Add API tests for `/chat`, loopback enforcement, worker failure handling, and bounded payloads. Add regression tests proving existing gateway and controller security behaviour remains unchanged. Run the complete pytest suite plus shell syntax, compilation, diff-check, and doctor diagnostics.

## Success Criteria
1. A caller can use the FastAPI backend as the single local control-plane entry point.
2. `POST /chat` works when the existing local memory/LLM worker is running.
3. The backend never accepts a non-loopback worker target.
4. Existing 59+ regression tests remain green.
5. The project remains usable with only local/open-source components and $0 mandatory cloud spend.
6. No privileged capability is silently enabled.
