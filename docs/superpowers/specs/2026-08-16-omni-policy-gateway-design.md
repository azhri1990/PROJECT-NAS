# PROJECT-NAS Omni Policy Gateway — Design Note

**Date:** 2026-08-16
**Status:** Implemented on `feat/omni-policy-gateway`; CI verification pending.
**Constraint:** $0 recurring cost; local-first; no required paid AI/API subscription.

## Objective

Create the first executable Omni Core security boundary without introducing a large agent framework. The boundary must prevent model-generated actions from directly reaching unrestricted host capabilities.

## Implemented Gate

The first Omni Core gate consists of:

1. Typed capabilities and risk levels in `runtime/policy.py`.
2. Deterministic allow/deny decisions through `PolicyEngine`.
3. A typed `ToolSpec` registry in `runtime/tool_gateway.py`.
4. Input validation before policy evaluation.
5. A policy check before every handler invocation.
6. Bounded handler timeout behavior.
7. JSON-serializable result enforcement.
8. Bounded audit events for allowed and denied requests.
9. One default read-only tool: `repo.progress`.
10. A FastAPI `/tools/{tool_name}` route that uses the gateway rather than arbitrary command execution.

## Security Boundary

`EXECUTE_PROCESS`, `NETWORK_ACCESS`, and `WRITE_REPOSITORY` are denied by default. The gateway accepts only registered tool names and validated structured payloads. No model-provided shell string, Python source, module path, or executable name is passed to a subprocess by the gateway.

The existing `/custom/{plugin_name}` endpoint remains a separate legacy surface and is not treated as equivalent to the new policy-gated tool boundary. Broad plugin autonomy is therefore still out of scope until a later repository-wide security review.

## Data Flow

```text
Request
  -> tool name + JSON payload
  -> registered ToolSpec
  -> input validator
  -> ToolRequest
  -> PolicyEngine
  -> bounded handler
  -> JSON result
  -> caller
```

Denied requests stop before the handler. Audit events retain only the tool name, decision, and policy reason and are capped in memory.

## Acceptance Criteria

- Read-only `repo.progress` requests can execute through the gateway.
- Unknown tools are rejected.
- Invalid progress arguments are rejected.
- Process, network, and repository-write capabilities are denied by default.
- Policy-denied handlers are never invoked.
- Tool timeouts surface as bounded failures.
- Non-JSON results are rejected.
- Backend requests use the gateway rather than arbitrary command execution.
- Existing runtime tests remain compatible.
- CI proves the critical paths on a clean environment.

## Next Gate

After CI verification, the next engineering gate is end-to-end `/chat` testing with fake local Ollama and isolated Chroma storage. Only after that should context budgeting, memory retention/redaction, and resource-aware local model routing be expanded.
