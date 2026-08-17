# PROJECT-NAS Completion Design

## Goal
Bring the current PROJECT-NAS repository to a defensible 100% engineering-complete baseline: every documented v1 runtime capability must exist, be policy-gated, tested, diagnosable, CI-reproducible, and consistent across PC and Termux/mobile configuration.

## Hard constraints
- Local-first and zero required paid cloud AI/API subscriptions.
- Local model endpoint must remain loopback-only by default.
- Tool execution remains deny-by-default for process execution, arbitrary network access, and repository writes.
- Runtime state must not be treated as source code or committed accidentally.
- No claim of completion without passing local-equivalent regression and CI.
- Preserve the existing public contracts unless a test proves the contract is incorrect.

## Current gaps found during baseline audit
1. README documents `status.health`, `prompt.get`, and `memory.read`, but the default gateway currently registers only `status.progress`.
2. Backend has a `health_report()` implementation but no `/health` endpoint and no gateway health tool.
3. Memory retrieval/read functionality exists but is not exposed through the control-plane gateway.
4. Prompt loading has a bounded helper but the gateway does not expose `prompt.get`.
5. The `/tools/{tool_name}` route therefore does not match the documented control-plane surface.
6. The current chat E2E test exercises the Flask memory service directly, but there is no complete control-plane integration test proving gateway/backend contracts together.
7. Model routing is currently a single configured model; there is no deterministic fallback/discovery contract.
8. Context budgeting is implemented only as hard character ceilings; there is no explicit deterministic budget allocation between static context, retrieved memory, and user input.
9. Memory persistence is trigger-based but lacks explicit redaction/retention controls.
10. Runtime controller ownership is tested, but readiness and externally-managed behavior need broader integration coverage.

## Architecture
The completion baseline keeps the existing layers and makes the interfaces explicit:

```text
CLI/controller
    |
    +--> Flask memory/chat service ----> local Ollama
    |          |                         |
    |          +--> bounded memory       +--> deterministic model selection
    |
    +--> FastAPI control plane
               |
               +--> ToolGateway
                       |
                       +--> PolicyEngine
                       +--> status.health
                       +--> status.progress
                       +--> prompt.get
                       +--> memory.read
```

The gateway remains the only control-plane execution path for tools. Each registered tool gets a strict input validator, capability, risk classification, bounded timeout, and audit record. Read-only v1 tools cannot invoke process, network, or repository-write capabilities.

## Components

### 1. Control-plane gateway
Register four documented read-only tools:
- `status.health`: returns the backend health report without memory contents.
- `status.progress`: returns bounded repository progress.
- `prompt.get`: returns bounded canonical prompt content with explicit truncation metadata.
- `memory.read`: returns bounded memory records, optionally filtered by query.

Validators reject unknown fields, malformed types, and out-of-range limits. All handlers are executed through the existing timeout wrapper.

### 2. Backend health and adapters
Expose `GET /health` and keep health evaluation deterministic. Health should distinguish `healthy`, `degraded`, and `unavailable`, with model availability treated as a core dependency. The backend must resolve configured paths at call time where tests alter environment variables, rather than relying on stale module-level paths.

### 3. Memory governance
Keep SQLite fallback and optional ChromaDB support. Add explicit bounded read validation, memory retention limits, and redaction of obvious secret/token patterns before persistence. Persistence remains opt-in through explicit memory language; ordinary chat must not write memory.

### 4. Chat/model routing
Add deterministic model discovery from local Ollama `/api/tags`. The configured model remains first choice. If unavailable, choose the first available model from a deterministic priority list or sorted local model list. Never call a remote endpoint. Preserve loopback enforcement.

### 5. Context budgeting
Replace independent maximums with a deterministic total prompt budget. Reserve space for system/runtime facts and user input, then allocate remaining budget to static context and retrieved memory. Truncation must be deterministic and observable in tests.

### 6. Runtime controller
Retain controller ownership protections. Add tests for startup when services are externally managed, PID/identity mismatch, readiness timeout, and successful owned lifecycle. The controller must never kill an externally managed service.

### 7. Verification
Expand tests to cover every documented API/tool contract, security boundary, malformed input path, fallback path, and controller lifecycle. CI must run shell validation, Python compilation, whitespace checks, tests, doctor, and progress reporting in a reproducible container.

## Success criteria
The baseline is considered complete only when:
- every README-documented v1 control-plane tool is registered and callable;
- policy tests prove denied capabilities cannot reach handlers;
- `/health`, `/tools/*`, `/prompt`, `/progress`, and `/chat` contracts are covered;
- local model fallback is deterministic and loopback-only;
- prompt/context/memory bounds are enforced deterministically;
- explicit memory persistence is bounded and redacted;
- runtime controller ownership is fail-closed;
- doctor and CI are green;
- documentation accurately describes implemented behavior and remaining non-v1 roadmap items;
- no test relies on a real Ollama service in CI.

## Non-goals for this completion pass
- unrestricted shell/process execution;
- arbitrary remote network tools;
- cloud AI dependencies;
- remote-device control;
- claiming unlimited compute or memory;
- building a full GUI before the runtime contracts are stable.
