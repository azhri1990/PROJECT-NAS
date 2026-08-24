# PROJECT-NAS / BOB / JARVIS Rules v1

**Status:** Canonical governance draft
**Date:** 2026-08-24

## Rule 1 — Source of truth
GitHub is the canonical project repository. Work is not considered integrated until committed and pushed.

## Rule 2 — No invented state
Never claim a component, fix, test result, merge, deployment, or capability exists unless repository evidence or explicit operator evidence supports the claim.

## Rule 3 — Preserve data
Do not discard project data, configuration, schemas, prompts, policies, tests, or historical evidence merely to simplify the repository. Deprecate explicitly instead.

## Rule 4 — Secrets never enter Git
Credentials, API keys, tokens, passwords, private keys, and other secrets must not be committed.

## Rule 5 — Fail closed
When authorization, policy, integrity, identity, or required verification is unavailable or ambiguous, consequential execution must stop rather than guess.

## Rule 6 — Human authority boundary
Memory, learning, confidence, recommendations, capability metadata, or model output cannot independently grant consequential execution authority.

## Rule 7 — Exact-action approval
Where approval is required, approval must bind to the exact consequential action and its relevant tool/version/payload identity. Policy must be re-evaluated immediately before execution.

## Rule 8 — BOB worker discipline
Workers must operate through defined worker/control-plane protocols. Worker identity, job ownership/lease, authorization, retries, recovery, and state transitions must be auditable.

## Rule 9 — Autopilot discipline
Autopilot may automate approved workflow, but escalation boundaries remain mandatory. High-risk, critical, process, network, or repository mutations must not bypass governance.

## Rule 10 — Verification before completion
A feature is not complete merely because code exists. Required tests, diagnostics, security checks, and relevant runtime verification must be recorded.

## Rule 11 — TDD for new behaviour
New behavioural capabilities should establish an executable contract/test before or alongside implementation, especially for security and control-plane invariants.

## Rule 12 — Cross-platform reality
PC, Android/Termux, and tablet behaviour must be treated as distinct runtime environments where dependencies or capabilities differ. Mobile compatibility must not be assumed from desktop success.

## Rule 13 — Auditability
Important decisions, state changes, approvals, failures, and recovery actions should leave machine-readable evidence where practical.

## Rule 14 — No silent authority escalation
A model, memory record, learned confidence value, plugin, worker, or capability registry must not silently increase its own execution authority.

## Rule 15 — Canonical handover
The repository must contain enough architecture, rules, data definitions, implementation state, verification evidence, and known limitations for another qualified AI/developer to continue the project without relying on private chat memory.
