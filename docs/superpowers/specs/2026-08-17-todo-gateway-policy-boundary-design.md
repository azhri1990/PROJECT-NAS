# TODO Gateway Policy Boundary Design

## Goal
Make the PROJECT-NAS ToolGateway the single policy/audit boundary for local TODO mutations while preserving the default-deny boundary for repository writes, process execution, and network access.

## Current Gap
`runtime/backend.py` exposes POST `/todos` and PUT `/todos/{todo_id}` handlers that write directly to SQLite. Those writes therefore bypass `ToolGateway.execute()`, `PolicyEngine.evaluate()`, and gateway audit logging. The existing gateway already provides bounded read tools for health, repository progress, prompt retrieval, and memory retrieval.

## Design

### 1. Capability model
Add a `WRITE_SESSION` capability to `runtime/policy.py`. This capability represents mutation of PROJECT-NAS local session state only; it is deliberately distinct from `WRITE_REPOSITORY`.

Policy behavior:
- `EXECUTE_PROCESS` remains denied by default.
- `NETWORK_ACCESS` remains denied by default.
- `WRITE_REPOSITORY` remains denied unless explicit approval is added later.
- `WRITE_SESSION` is allowed only for low-risk, explicitly registered session tools.
- High and critical risk remain denied by default.

### 2. Gateway tools
Extend `runtime/tool_gateway.py` with bounded TODO tools:
- `todo.create`
- `todo.update`
- `todo.list`

All TODO inputs are validated before policy evaluation and before SQLite is touched.

Validation requirements:
- Payload must be an object.
- IDs and titles must be non-empty strings with bounded lengths.
- Description is optional and bounded.
- Status is restricted to the existing TODO lifecycle values used by the backend.
- Unknown fields are rejected.
- Update requires a valid TODO ID and permits only title, description, and status changes.
- List accepts no unrecognized arguments and supports a bounded result limit if needed by the existing API contract.

### 3. Persistence boundary
Keep SQLite access in `runtime/backend.py` behind small internal functions. The gateway handlers call those functions; HTTP endpoints call the gateway rather than writing directly.

The existing REST contract remains stable:
- `GET /todos` returns `{ "todos": [...] }`.
- `POST /todos` returns `201`-style application behavior currently represented by the existing response body and preserves duplicate-ID conflict behavior.
- `PUT /todos/{todo_id}` preserves not-found behavior and update semantics.

No repository files are mutated by TODO operations.

### 4. Audit behavior
Every accepted or rejected TODO tool request is recorded by `ToolGateway.audit_log`, using the existing bounded audit mechanism. HTTP-level validation failures that occur before gateway invocation are minimized by moving validation into the gateway so policy and audit decisions remain observable.

### 5. Security invariants
Regression tests must prove:
1. `WRITE_REPOSITORY` remains denied.
2. `EXECUTE_PROCESS` remains denied.
3. `NETWORK_ACCESS` remains denied.
4. Unknown namespaces remain denied.
5. TODO mutation reaches SQLite only after gateway validation and policy approval.
6. Invalid TODO payloads do not invoke persistence handlers.
7. TODO operations do not acquire repository-write capability.
8. Gateway audit entries are retained within the configured audit limit.

### 6. Compatibility and scope
Do not redesign the entire backend, database schema, or authentication model. Do not add external dependencies. Preserve the local-first architecture and existing SQLite fallback. This change is intentionally limited to closing the policy bypass created by direct TODO writes.

## Data Flow

`HTTP /todos` -> `ToolGateway.execute()` -> input validator -> `PolicyEngine.evaluate()` -> bounded persistence handler -> SQLite

For reads:

`HTTP /todos` -> `ToolGateway.execute()` -> bounded read handler -> SQLite

For repository/process/network capabilities:

`request` -> `PolicyEngine.evaluate()` -> deny by default

## Testing Strategy

Use TDD. Add focused gateway and backend regression tests first, then implement the smallest changes necessary to pass them. Run the focused tests, the complete pytest suite, `git diff --check`, and the project's existing doctor/CI verification commands before completion.

## Success Criteria

The gap is closed when no `/todos` HTTP mutation performs a direct SQLite write outside the gateway path, all security invariants above are covered by automated tests, the full suite passes, and the resulting branch is cleanly reviewable as one focused security/architecture change.
