# BOB-7 Persistent Worker Supervisor

## Goal

Provide durable worker lifecycle and recovery state without granting execution authority or requiring paid infrastructure.

## Scope

1. Persist worker lifecycle state atomically.
2. Restore state after process death/restart.
3. Track heartbeats and detect stale workers.
4. Produce deterministic reconnect decisions.
5. Track restart/reconnect/recovery counters.
6. Recover safely without executing commands from supervisor state.
7. Fail closed on worker identity mismatch.
8. Keep NAS PolicyEngine/ToolGateway authoritative for execution.
9. Validate the subsystem with focused tests and full repository CI.

## Non-goals

- No public Internet tunnel.
- No arbitrary shell execution.
- No OS-level guarantee that Android will keep a process alive indefinitely.
- No paid cloud dependency.

## Recovery contract

`heartbeat stale -> offline -> reconnect -> re-register/heartbeat -> ready`.

A process crash may lose in-memory state, but the last durable supervisor state remains available. Job lease recovery stays owned by BOB's existing lease layer; the supervisor only records recovery outcomes.

## Verification

- focused supervisor tests
- Python compilation and repository checks
- full PROJECT-NAS pytest suite
- runtime smoke/integration workflows
