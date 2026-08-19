# PROJECT-BOB BOB-3 — Autonomous Build Orchestrator

## Purpose

BOB-3 turns the BOB control plane into a bounded scheduler for long-running work. It can make deterministic decisions about **start, defer, retry, and fail** based on worker availability and declared resource state.

## Zero-cost rule

The orchestrator has no required paid AI/API dependency. Local workers and local inference are preferred. GitHub remains source control/CI, not a 24/7 compute substrate.

## Resource-aware routing

Workers report a `ResourceSnapshot` containing:

- online state
- CPU load
- available memory
- available storage
- local inference availability

BOB uses those values only for scheduling decisions. It does not inspect or control the host directly.

## Recovery

Failures receive a bounded retry budget. Once the retry budget is exhausted, the job transitions to `failed` rather than retrying forever.

A resource mismatch results in **defer**, not forced execution.

## Authority boundary

BOB remains an orchestrator. It does not expose a shell, grant permissions, or bypass `PROJECT-NAS` PolicyEngine/ToolGateway controls. Actual worker execution remains outside this module.

## Intended lifecycle

`created → queued → dispatched → running → succeeded`

Failure path:

`running → queued (bounded retry) → failed`

Resource path:

`dispatched → deferred decision → scheduler can retry later`

## Future work

- persist queue state across process restarts
- connect worker heartbeat data to resource snapshots
- add durable scheduler leases
- add mobile status streaming
- integrate build/test result ingestion
- add automatic rollback proposal generation
