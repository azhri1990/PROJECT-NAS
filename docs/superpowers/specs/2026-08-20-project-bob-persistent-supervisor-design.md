# BOB-7 Persistent Worker Supervisor Design

## Principles

- Lifecycle management is separate from authorization and execution.
- State is persisted atomically so crashes do not corrupt the state file.
- Heartbeat freshness drives deterministic health decisions.
- Recovery is bounded and observable.
- Worker identity mismatches fail closed.
- Android background execution remains subject to Android/Termux OS limits.

## State machine

`starting -> ready -> offline -> ready` for recovery.

`ready -> stopping -> stopped` is terminal for that supervisor instance.

## Persistence

State is written to a temporary sibling file and atomically replaced. This prevents partially written JSON from becoming the active state file during a process interruption.

## Security boundary

The supervisor does not accept or execute arbitrary commands. It can invoke a caller-provided restart callback, but that callback is an application integration point; authorization remains outside the supervisor. BOB/NAS policy must be applied before any job execution.
