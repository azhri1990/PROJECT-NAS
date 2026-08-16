# Omni Policy Gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first executable Omni Core security boundary: typed capabilities, policy decisions, and a tool gateway that can expose read-only tools without allowing model output to execute arbitrary host actions.

**Architecture:** Keep the existing FastAPI backend intact and add small, dependency-light runtime modules behind explicit interfaces. A `ToolSpec` declares capability and validation requirements; a `PolicyEngine` converts a requested action into an allow/deny decision; `ToolGateway` executes only registered tools after policy approval and records a bounded audit event. The first shipped tool is a safe repository-progress read, so the new boundary is exercised without introducing write or shell execution.

**Tech Stack:** Python 3.12+, FastAPI, pytest, existing PROJECT-NAS runtime modules; no new paid service and no mandatory cloud dependency.

## Global Constraints

- `$0 recurring cost; local-first; no required paid AI/API subscription`.
- `No arbitrary command execution from model output.`
- `Every tool has a typed contract, capability declaration, input validation, timeout, resource limit, and audit event.`
- `Explicit approval for destructive or irreversible actions.`
- `Local-only network exposure by default.`
- `Retrieved memory and external content treated as untrusted data.`
- `A failed security or policy gate must not be bypassed by fallback models.`
- `A feature is not complete until behavior is executable, tested, documented accurately, and reproducible on a clean environment.`

---

### Task 1: Define capability and policy primitives

**Files:**
- Create: `runtime/policy.py`
- Test: `tests/test_policy.py`

**Interfaces:**
- Produces `Capability` enum values: `READ_REPOSITORY`, `READ_RUNTIME`, `WRITE_REPOSITORY`, `EXECUTE_PROCESS`, `NETWORK_ACCESS`.
- Produces `RiskLevel` enum values: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
- Produces `ToolRequest(tool_name: str, capability: Capability, risk: RiskLevel, input: dict)`.
- Produces `PolicyDecision(allowed: bool, reason: str)`.
- Produces `PolicyEngine.evaluate(request: ToolRequest) -> PolicyDecision`.

- [ ] **Step 1: Write failing tests for safe and unsafe policy decisions**

```python
from runtime.policy import Capability, PolicyEngine, RiskLevel, ToolRequest


def test_read_repository_is_allowed_for_low_risk_request():
    request = ToolRequest(
        tool_name="repo.progress",
        capability=Capability.READ_REPOSITORY,
        risk=RiskLevel.LOW,
        input={},
    )
    decision = PolicyEngine().evaluate(request)
    assert decision.allowed is True


def test_process_execution_is_denied_by_default():
    request = ToolRequest(
        tool_name="shell.run",
        capability=Capability.EXECUTE_PROCESS,
        risk=RiskLevel.CRITICAL,
        input={"command": "whoami"},
    )
    decision = PolicyEngine().evaluate(request)
    assert decision.allowed is False
    assert "execute_process" in decision.reason


def test_write_requires_explicit_approval():
    request = ToolRequest(
        tool_name="repo.write",
        capability=Capability.WRITE_REPOSITORY,
        risk=RiskLevel.HIGH,
        input={"path": "x.txt"},
    )
    decision = PolicyEngine().evaluate(request)
    assert decision.allowed is False
    assert "approval" in decision.reason
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `python -m pytest tests/test_policy.py -q`
Expected: collection failure because `runtime.policy` does not exist yet.

- [ ] **Step 3: Implement the minimal policy model**

```python
from dataclasses import dataclass
from enum import Enum


class Capability(str, Enum):
    READ_REPOSITORY = "read_repository"
    READ_RUNTIME = "read_runtime"
    WRITE_REPOSITORY = "write_repository"
    EXECUTE_PROCESS = "execute_process"
    NETWORK_ACCESS = "network_access"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ToolRequest:
    tool_name: str
    capability: Capability
    risk: RiskLevel
    input: dict


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


class PolicyEngine:
    def evaluate(self, request: ToolRequest) -> PolicyDecision:
        if request.capability in {
            Capability.EXECUTE_PROCESS,
            Capability.NETWORK_ACCESS,
        }:
            return PolicyDecision(False, f"capability {request.capability.value} denied by default")
        if request.capability == Capability.WRITE_REPOSITORY:
            return PolicyDecision(False, "write_repository requires explicit approval")
        if request.risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            return PolicyDecision(False, "high-risk action requires explicit approval")
        return PolicyDecision(True, "allowed by local read-only policy")
```

- [ ] **Step 4: Run focused tests and the existing suite**

Run: `python -m pytest tests/test_policy.py -q && python -m pytest -q`
Expected: all policy tests pass and the pre-existing suite remains green.

- [ ] **Step 5: Commit**

```bash
git add runtime/policy.py tests/test_policy.py
git commit -m "feat: add Omni policy primitives"
```

### Task 2: Build the typed tool gateway

**Files:**
- Create: `runtime/tool_gateway.py`
- Test: `tests/test_tool_gateway.py`

**Interfaces:**
- Produces `ToolSpec(name: str, capability: Capability, risk: RiskLevel, input_validator: Callable[[dict], dict], handler: Callable[[dict], object], timeout_seconds: float = 5.0)`.
- Produces `ToolGateway.register(spec: ToolSpec) -> None`.
- Produces `ToolGateway.execute(name: str, payload: dict) -> object`.
- Gateway must call `PolicyEngine.evaluate()` before a handler and raise `PermissionError` on denial.
- Gateway must reject unknown tools, invalid payloads, non-positive timeout values, and handler results that cannot be JSON-serialized.

- [ ] **Step 1: Write failing registration/execution tests**

```python
import pytest
from runtime.policy import Capability, RiskLevel
from runtime.tool_gateway import ToolGateway, ToolSpec


def identity(payload):
    return payload


def test_registered_read_tool_executes_after_policy_check():
    gateway = ToolGateway()
    gateway.register(ToolSpec(
        name="repo.progress",
        capability=Capability.READ_REPOSITORY,
        risk=RiskLevel.LOW,
        input_validator=identity,
        handler=identity,
    ))
    assert gateway.execute("repo.progress", {"commits": 3}) == {"commits": 3}


def test_unknown_tool_is_rejected():
    with pytest.raises(KeyError):
        ToolGateway().execute("missing", {})


def test_denied_capability_never_calls_handler():
    called = []
    gateway = ToolGateway()
    gateway.register(ToolSpec(
        name="shell.run",
        capability=Capability.EXECUTE_PROCESS,
        risk=RiskLevel.CRITICAL,
        input_validator=identity,
        handler=lambda payload: called.append(payload),
    ))
    with pytest.raises(PermissionError):
        gateway.execute("shell.run", {"command": "whoami"})
    assert called == []
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `python -m pytest tests/test_tool_gateway.py -q`
Expected: collection failure because `runtime.tool_gateway` does not exist.

- [ ] **Step 3: Implement registry, validation, policy gate, timeout, and audit record**

```python
from dataclasses import dataclass
from typing import Any, Callable
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from runtime.policy import Capability, PolicyEngine, RiskLevel, ToolRequest


@dataclass(frozen=True)
class ToolSpec:
    name: str
    capability: Capability
    risk: RiskLevel
    input_validator: Callable[[dict], dict]
    handler: Callable[[dict], Any]
    timeout_seconds: float = 5.0


class ToolGateway:
    def __init__(self, policy=None):
        self.policy = policy or PolicyEngine()
        self._tools = {}
        self.audit_log = []

    def register(self, spec: ToolSpec) -> None:
        if not spec.name or spec.name in self._tools:
            raise ValueError("tool name must be unique and non-empty")
        if spec.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._tools[spec.name] = spec

    def execute(self, name: str, payload: dict) -> Any:
        if name not in self._tools:
            raise KeyError(name)
        spec = self._tools[name]
        validated = spec.input_validator(payload)
        request = ToolRequest(name, spec.capability, spec.risk, validated)
        decision = self.policy.evaluate(request)
        self.audit_log.append({"tool": name, "allowed": decision.allowed, "reason": decision.reason})
        if not decision.allowed:
            raise PermissionError(decision.reason)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(spec.handler, validated)
            try:
                result = future.result(timeout=spec.timeout_seconds)
            except FutureTimeoutError as exc:
                future.cancel()
                raise TimeoutError(f"tool timed out: {name}") from exc
        json.dumps(result)
        return result
```

- [ ] **Step 4: Add validation and timeout tests, then run the suite**

Run: `python -m pytest tests/test_tool_gateway.py -q && python -m pytest -q`
Expected: gateway tests and all existing tests pass.

- [ ] **Step 5: Commit**

```bash
git add runtime/tool_gateway.py tests/test_tool_gateway.py
git commit -m "feat: add typed Omni tool gateway"
```

### Task 3: Register a safe repository-progress tool

**Files:**
- Modify: `runtime/tool_gateway.py`
- Modify: `runtime/backend.py`
- Test: `tests/test_tool_gateway.py`
- Test: `tests/test_backend.py`

**Interfaces:**
- Produces `build_default_gateway() -> ToolGateway`.
- Registers only `repo.progress` in v1.
- `repo.progress` accepts `{}` or `{"commits": integer}` where `1 <= commits <= 50`.
- The handler delegates to existing `backend.run_git_info()` and does not expose arbitrary git arguments.

- [ ] **Step 1: Write the failing integration test**

```python
def test_default_gateway_exposes_only_bounded_repository_progress():
    from runtime.tool_gateway import build_default_gateway

    gateway = build_default_gateway()
    result = gateway.execute("repo.progress", {"commits": 2})
    assert set(result) == {"branch", "status_porcelain", "recent_commits"}
    assert len(result["recent_commits"]) <= 2


def test_progress_validator_rejects_arbitrary_git_arguments():
    from runtime.tool_gateway import build_default_gateway

    gateway = build_default_gateway()
    for payload in ({"command": "git reset --hard"}, {"commits": 0}, {"commits": 51}):
        with pytest.raises((ValueError, PermissionError)):
            gateway.execute("repo.progress", payload)
```

- [ ] **Step 2: Run the focused integration tests and verify failure**

Run: `python -m pytest tests/test_tool_gateway.py -q`
Expected: `build_default_gateway` is not defined.

- [ ] **Step 3: Implement the bounded validator and registration**

```python
def _validate_progress(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    allowed = {"commits"}
    if set(payload) - allowed:
        raise ValueError("unsupported progress arguments")
    commits = payload.get("commits", 10)
    if not isinstance(commits, int) or isinstance(commits, bool) or not 1 <= commits <= 50:
        raise ValueError("commits must be an integer from 1 to 50")
    return {"commits": commits}


def build_default_gateway():
    from runtime.backend import run_git_info
    gateway = ToolGateway()
    gateway.register(ToolSpec(
        name="repo.progress",
        capability=Capability.READ_REPOSITORY,
        risk=RiskLevel.LOW,
        input_validator=_validate_progress,
        handler=lambda payload: run_git_info(payload["commits"]),
    ))
    return gateway
```

- [ ] **Step 4: Run backend and gateway tests**

Run: `python -m pytest tests/test_backend.py tests/test_tool_gateway.py -q`
Expected: all focused tests pass.

- [ ] **Step 5: Commit**

```bash
git add runtime/tool_gateway.py runtime/backend.py tests/test_tool_gateway.py tests/test_backend.py
git commit -m "feat: expose bounded repository progress tool"
```

### Task 4: Add the gateway endpoint without exposing direct execution

**Files:**
- Modify: `runtime/backend.py`
- Test: `tests/test_backend.py`

**Interfaces:**
- Adds `POST /tools/{tool_name}` accepting a JSON object and returning the gateway result.
- Returns HTTP 404 for unknown tools, 400 for invalid payloads, 403 for policy denial, and 504 for timeout.
- The endpoint must not accept shell commands, module paths, Python code, or arbitrary executable names.

- [ ] **Step 1: Write failing API tests**

```python
from fastapi.testclient import TestClient


def test_tool_endpoint_allows_repo_progress():
    backend = load_backend()
    client = TestClient(backend.app)
    response = client.post("/tools/repo.progress", json={"commits": 1})
    assert response.status_code == 200
    assert "recent_commits" in response.json()


def test_tool_endpoint_rejects_unknown_tool():
    backend = load_backend()
    client = TestClient(backend.app)
    response = client.post("/tools/shell.run", json={"command": "whoami"})
    assert response.status_code in {403, 404}
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `python -m pytest tests/test_backend.py -q`
Expected: the new `/tools/...` route is not registered.

- [ ] **Step 3: Add a module-level gateway and route**

```python
from runtime.tool_gateway import build_default_gateway

TOOL_GATEWAY = build_default_gateway()


@app.post("/tools/{tool_name}")
async def execute_tool(tool_name: str, payload: Dict[str, Any]):
    try:
        return TOOL_GATEWAY.execute(tool_name, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="tool not found")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
```

- [ ] **Step 4: Run all tests and compile runtime modules**

Run: `python -m pytest -q && python -m compileall -q runtime tests`
Expected: all tests pass and compilation exits 0.

- [ ] **Step 5: Commit**

```bash
git add runtime/backend.py tests/test_backend.py
git commit -m "feat: gate backend tool execution through policy"
```

### Task 5: Document and verify the first Omni Core gate

**Files:**
- Modify: `ACTION-PLAN.md`
- Modify: `Obsidian/04-Project/Project-Status.md`
- Create: `docs/superpowers/specs/2026-08-16-omni-policy-gateway-design.md`

**Interfaces:**
- Documentation must state that v1 exposes one read-only repository-progress tool through the policy gateway.
- Documentation must explicitly state that shell/process/network/write capabilities remain denied by default.

- [ ] **Step 1: Write the acceptance assertions into the design note**

```markdown
## Implemented Gate

The first Omni Core gate consists of typed capabilities, deterministic policy decisions, a bounded tool registry, audit events, and one read-only `repo.progress` tool.

### Security boundary

`EXECUTE_PROCESS`, `NETWORK_ACCESS`, and `WRITE_REPOSITORY` are denied by default. The gateway validates inputs before policy evaluation and never executes model-provided shell text.
```

- [ ] **Step 2: Update the action plan and project status**

Run: edit `ACTION-PLAN.md` so the next engineering gate records the policy/tool gateway as completed and promotes end-to-end chat testing, context budgeting, memory policy, and model routing to the next gates. Update `Obsidian/04-Project/Project-Status.md` to replace the stale “finish runtime reliability/security gates” wording with the actual gateway state.

- [ ] **Step 3: Run the complete verification set**

Run: `python -m pytest -q && python -m compileall -q runtime tests`
Expected: all tests pass and compilation exits 0.

- [ ] **Step 4: Inspect the branch diff against main**

Run: `git diff main...HEAD --check`
Expected: no whitespace errors.

- [ ] **Step 5: Commit documentation**

```bash
git add ACTION-PLAN.md Obsidian/04-Project/Project-Status.md docs/superpowers/specs/2026-08-16-omni-policy-gateway-design.md
git commit -m "docs: record Omni policy gateway security gate"
```

### Completion Gate

- [ ] All focused tests pass.
- [ ] Full pytest suite passes.
- [ ] Runtime and tests compile cleanly.
- [ ] `repo.progress` is the only default tool.
- [ ] Process, network, and repository-write capabilities remain denied by default.
- [ ] No model-generated string is passed to `subprocess` by the gateway.
- [ ] Audit records exist for allowed and denied tool attempts.
- [ ] Documentation matches the executable behavior.
