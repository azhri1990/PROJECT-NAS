# PROJECT-NAS Control Plane v1 Design

## Status

Approved design based on the user's selected requirements.

## Goal

Turn the existing Tool Gateway from a policy/security shell into a useful, deterministic, read-only local control plane for PROJECT-NAS. The control plane must expose bounded runtime, repository, prompt, and memory information without granting arbitrary process, network, or repository-write capabilities.

## Current Context

The runtime already has a bounded Tool Gateway with namespace allowlisting, input validation, policy evaluation, audit logging, and per-tool execution timeouts. The default gateway currently registers `status.progress`. The memory injector provides local SQLite/ChromaDB-backed memory retrieval and explicit memory persistence, with bounded prompt/context/response limits. Existing regression coverage is 59 passing tests.

## Control Plane Contract

### `status.health`

Return one deterministic aggregate status plus per-component diagnostics.

Aggregate states:

- `healthy`: all required components pass.
- `degraded`: PROJECT-NAS remains usable, but one or more components fail.
- `unavailable`: the core runtime cannot function.

Components should cover:

- Ollama endpoint availability.
- Memory API availability.
- Memory SQLite storage accessibility and record count where applicable.
- Repository state/readability.
- Configured model availability.

Failures must be represented explicitly rather than hidden behind an `ok` result. Health checks must use bounded local operations and must not mutate state.

### `status.progress`

Retain the existing bounded repository-progress tool. `commits` defaults to 10 and is restricted to 1..50.

### `prompt.get`

Return structured canonical prompt information:

```json
{
  "path": "...",
  "content": "...",
  "chars": 1234,
  "truncated": false
}
```

The content must be bounded by a configured maximum. The response must explicitly indicate truncation. The implementation should prefer the canonical `ai/MASTER_PROMPT.md` path and preserve the existing fallback behavior where appropriate.

### `memory.read`

Support both recent-memory and query-based retrieval:

- `{}` → bounded recent memories.
- `{ "limit": 5 }` → bounded recent memories.
- `{ "query": "runtime" }` → bounded relevant memories.
- `{ "query": "runtime", "limit": 5 }` → bounded relevant memories.

The default limit must be bounded. The maximum limit must be bounded. Query and limit inputs must be strictly validated.

Return structured records containing actual stored data and metadata where available:

```json
{
  "memories": [
    {
      "id": "...",
      "document": "...",
      "metadata": {}
    }
  ],
  "count": 1
}
```

Do not fabricate similarity scores. The current SQLite adapter performs deterministic TF-IDF-lite retrieval but its public result does not currently expose scores; therefore no synthetic score field should be added.

## Architecture

```text
LLM / API client
      |
      v
Tool Gateway
      |
      +-- namespace allowlist
      +-- input validation
      +-- policy evaluation
      +-- audit record
      +-- execution timeout
      |
      v
Read-only Control Plane Tools
      |
      +-- status.health
      +-- status.progress
      +-- prompt.get
      +-- memory.read
      |
      v
Local runtime / repository / prompt / SQLite memory
```

The LLM must never receive a direct arbitrary shell, process, network, or repository-write primitive through this control plane.

## Security Requirements

1. Keep `memory`, `prompt`, and `status` as the only default namespaces.
2. Preserve denial of `EXECUTE_PROCESS` and `NETWORK_ACCESS` capabilities.
3. Preserve default denial of `WRITE_REPOSITORY` without explicit approval.
4. Validate payloads before invoking handlers.
5. Bound every externally supplied count, query, and content length.
6. Keep tool execution timeouts finite.
7. Record allow/deny decisions in the existing audit log.
8. Health and read operations must not mutate project or memory state.
9. Never expose full database contents when a bounded result is sufficient.

## API Integration

The existing `/tools/{tool_name}` backend endpoint remains the transport boundary. It should expose the four registered control-plane tools through the existing gateway rather than introducing a second execution mechanism.

Existing HTTP error semantics remain:

- 404 for unknown tool.
- 403 for policy denial.
- 400 for invalid payload.
- 504 for tool timeout.

## Testing Strategy

Extend the existing gateway suite rather than replacing it.

Required coverage:

1. Each of the four default tools is registered and executable.
2. `memory.read` supports recent mode, query mode, combined mode, empty results, default limit, and maximum-limit enforcement.
3. `prompt.get` returns metadata and correctly reports truncation.
4. `status.health` reports healthy state when all dependencies pass.
5. `status.health` reports degraded state when a non-core dependency fails.
6. `status.health` reports unavailable state when the core runtime is unavailable.
7. Health checks are bounded and do not mutate state.
8. Invalid payloads are rejected before handlers execute.
9. Non-allowlisted namespaces remain denied.
10. Write/process/network capabilities remain denied.
11. Audit records are created for allow and deny decisions.
12. Existing 59-test regression suite remains green.

## Non-Goals

This milestone does not add:

- arbitrary shell execution;
- autonomous repository modification;
- network tools;
- write-capable tools;
- vector-database migration;
- fabricated memory similarity scores;
- UI work;
- cloud AI dependencies;
- paid API/token dependencies.

## Success Criteria

The milestone is complete when the four control-plane tools are implemented behind the existing gateway, fully tested, exposed through `/tools/{tool_name}`, security boundaries remain intact, and the complete regression suite passes with no `git diff --check` errors.
