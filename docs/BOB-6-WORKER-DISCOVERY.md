# BOB-6 — Worker Discovery & Capability Orchestration

BOB-6 adds an advisory discovery/ranking layer over the BOB-4 worker protocol and BOB-5 Android worker.

## Rules

1. Worker registration and heartbeat determine freshness.
2. Capabilities are eligibility hints, never authorization.
3. Stale/offline workers are excluded.
4. Required capabilities must be present before routing.
5. Resource availability is used only for ranking.
6. NAS PolicyEngine/ToolGateway remains the final execution authority.
7. No public tunnel or paid service is required.

## Current implementation

`runtime/bob/discovery.py` provides deterministic worker snapshots, freshness checks, ranking, and selection. It is intentionally transport-agnostic so the same logic can later drive HTTP polling or a persistent relay.

## Next deployment step

When an Android worker and PC worker are online, their existing BOB-4/5 registration and heartbeat data can be adapted into `WorkerSnapshot` values. BOB can then prefer a capable PC for heavy builds while retaining Android as a lightweight fallback.
