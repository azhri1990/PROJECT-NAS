# PROJECT-NAS Core Hardening Design

## Goal
Build a zero-cost, local-first PROJECT-NAS runtime that has one governed execution boundary, bounded memory, deterministic policy, local-model routing/fallback, lifecycle safety, and regression coverage across PC and Termux.

## Architecture
- `runtime/orchestrator.py`: intent-to-plan execution coordinator and verification boundary.
- `runtime/tool_gateway.py`: sole capability execution gateway; validates, authorizes, times out, and audits tools.
- `runtime/policy.py`: deterministic capability/risk policy.
- `runtime/ai_router.py`: local model discovery, selection, fallback, and bounded request construction.
- `runtime/memory.py`: common memory interface over SQLite and optional ChromaDB.
- `runtime/audit.py`: bounded structured audit events.
- `runtime/backend.py`: HTTP adapter; business actions must use governed services/gateway.
- `runtime/project-nas.sh`: runtime lifecycle and CLI adapter.
- `runtime/doctor.py`: health and dependency diagnostics.

## Security contracts
1. Process execution and arbitrary network access are denied by default.
2. Repository writes require explicit approval.
3. High/critical-risk capabilities require explicit approval.
4. Payload validation happens before handler invocation.
5. Every tool has a finite timeout.
6. Denied and allowed tool decisions are audit-recorded.
7. Unknown namespaces cannot bypass policy.
8. Runtime stop may terminate only processes whose PID and process identity match controller-owned state.

## Memory contracts
- SQLite is the guaranteed fallback and persistence layer.
- ChromaDB is optional and must not be required for startup.
- Retrieval is deterministic/bounded and respects memory/context character limits.
- Persistence is explicit and governed rather than inferred from every interaction.

## AI contracts
- Ollama/local models are the default.
- No paid API, token credit, or cloud subscription is required.
- Model availability is detected at runtime.
- Router falls back to another installed local model when the preferred model is unavailable.
- Prompt, context, and response sizes remain bounded.

## API contracts
- `/prompt`, `/progress`, and governed `/tools/{tool}` remain available.
- Direct TODO CRUD is not permitted to become a security bypass; it will either be governed or explicitly isolated as a non-agent API surface.
- Health and diagnostics must work when optional AI/vector dependencies are absent.

## Testing
Maintain the existing 59-test baseline and add contract tests for gateway coverage, policy decisions, orchestrator verification, AI fallback, memory fallback, API authorization, lifecycle ownership, and failure modes. The target is zero known failing tests and no untested security bypass introduced by the upgrade.

## Scope discipline
This phase hardens the core runtime. It does not attempt to implement every future JARVIS feature. New capabilities must enter through the same gateway and policy contracts.
