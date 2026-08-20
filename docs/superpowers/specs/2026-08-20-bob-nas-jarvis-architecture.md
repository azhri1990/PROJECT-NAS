# BOB → NAS → JARVIS Architecture Specification

## Status
Approved by Nash on 2026-08-20.

## Goal
Build a zero-cost, local-first autonomous stack in which PROJECT-BOB is the builder/supervisor, PROJECT-NAS is the operating core, and JARVIS is the human-facing intelligence/interface layer.

## Architecture
```text
YOU
 │
 ▼
JARVIS — interface / intelligence
 │
 ▼
PROJECT-NAS — personal operating core
 │
 ▼
PROJECT-BOB — build / QA / recovery supervisor
 │
 ├── PC
 ├── Tablet
 └── Phone / Termux
```

BOB must not duplicate NAS or JARVIS responsibilities. NAS owns runtime capabilities, memory, tools, policy and automation. JARVIS owns conversational/agent interaction and delegates execution. BOB owns building, testing, verification, recovery and failure learning.

## Core Principles
1. Never assume; verify with evidence.
2. Never claim CI verification without an actual run tied to the exact revision.
3. Every failure becomes: failure class → root cause → lesson → prevention → regression evidence.
4. Known failure classes must not silently repeat; they escalate when prevention does not resolve them.
5. Fail closed on authorization, verification, or safety uncertainty.
6. Routine work proceeds without repeated human approval.
7. Major architectural, destructive, security-sensitive, or cost-changing decisions require Nash.
8. $0/local-first remains a hard constraint; local/open-source tooling is preferred.
9. State must be persistent and auditable.
10. The system must learn from failures structurally, not depend on conversational memory.

## Build Stages
### Stage 1 — BOB control plane
Learning ledger, supervisor/watchdog, task lifecycle, evidence-based verification, bounded recovery and escalation.

### Stage 2 — NAS integration
BOB becomes the controlled builder for PROJECT-NAS. Existing NAS policy and security boundaries remain authoritative.

### Stage 3 — JARVIS integration
JARVIS becomes the user-facing intelligence/interface and delegates controlled work through NAS/BOB.

### Stage 4 — Device/runtime integration
PC is the primary build node; mobile/Termux and tablet provide supervision/control endpoints. Persistent state and recovery are mandatory.

### Stage 5 — 24/7 hardening
Failure injection, recovery tests, exact-SHA verification, auditability, fail-closed behavior and operational runbooks.

## Verification Contract
A component is only `VERIFIED` when evidence exists for the exact revision under test.

Allowed states:
- `NOT_TRIGGERED` — no applicable CI run exists.
- `RUNNING` — an applicable run exists but is incomplete.
- `FAILED` — the applicable run completed unsuccessfully.
- `VERIFIED` — the applicable run completed successfully against the exact revision.

## Success Criteria
- BOB can build/test NAS without requiring routine human intervention.
- BOB records and reuses failure lessons.
- Repeated failure classes escalate instead of looping indefinitely.
- CI verification is observable and exact-revision based.
- NAS remains policy-controlled and auditable.
- JARVIS delegates rather than bypasses policy.
- The integrated stack can recover from bounded failures and stop safely on unsafe/unknown conditions.
