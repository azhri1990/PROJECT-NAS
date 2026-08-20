# PROJECT-BOB AUTO PILOT Governance v1

## Goal
Establish a deterministic governance layer that lets PROJECT-BOB operate autonomously for low/medium-risk engineering work while escalating major architectural, security, cost, data, governance, and destructive decisions to Nash.

## Existing baseline
PROJECT-NAS already has a local-first PolicyEngine and ToolGateway, plus BOB orchestration, worker discovery, persistent supervision, and Android/Termux worker support. This phase extends those boundaries rather than replacing them.

## Decision model
Every BOB task is classified before execution:

- LOW: routine read-only, testing, documentation, deterministic repair, and equivalent internal refactoring.
- MEDIUM: bounded source/config changes that remain inside approved architecture and policy.
- HIGH: privileged capabilities, security-boundary changes, external data transfer, major dependency or architecture changes, or destructive operations.
- CRITICAL: policy bypass, secret exposure, irreversible destruction, authority-boundary changes, or recurring paid services.

LOW and MEDIUM work may proceed autonomously when policy permits. HIGH and CRITICAL work requires explicit Nash approval. Unknown risk or unknown verification fails closed.

## Safety rules
1. BOB never grants itself capabilities.
2. Model output is untrusted input.
3. External content is treated as potentially hostile and cannot override policy.
4. Tool execution remains behind the NAS PolicyEngine/ToolGateway.
5. Protected governance, security, and audit resources cannot be changed by ordinary autonomous tasks.
6. Every autonomous decision produces an auditable decision record.
7. Every verified failure must produce a regression test or a stronger preventive control where practical.
8. Repeated failure of the same strategy triggers a circuit breaker instead of infinite retries.
9. Successful implementation is not equivalent to verification; unverified work fails closed.
10. The architecture remains $0/local-first; paid services require explicit Nash approval.

## Learning loop
Failure -> reproduce -> root-cause -> repair -> regression/prevention control -> verify -> record lesson.

Lessons are non-authoritative until verified. Learning data cannot grant capabilities, alter policy, or mutate source code by itself.

## Autopilot loop
Inspect state -> select task -> classify risk -> policy check -> execute -> test -> security check -> verify -> commit -> update decision/learning records -> select next task.

Unknown failures pause the affected task and escalate. Safe known fixes may be retried within a bounded budget.

## Approval boundary
Nash approval is mandatory for:
- constitutional/governance changes;
- security-boundary weakening or privileged execution;
- major architecture changes;
- external transmission of sensitive/private data;
- recurring or non-zero cost;
- destructive or irreversible operations;
- changes that materially alter BOB/JARVIS/NAS authority boundaries.

## Testing
New governance behavior must use TDD. CI remains the reproducible verification gate. A task cannot be marked complete without evidence from tests/checks appropriate to the change.

## Non-goals
This phase does not add unrestricted shell execution, paid AI services, automatic policy mutation, automatic deployment to production, or a new database architecture.

## Success criteria
- Governance decisions are deterministic and testable.
- Major decisions are represented as explicit approval-required records.
- Known failure recurrence is detectable and bounded.
- Learning records cannot become authority.
- Existing PolicyEngine/ToolGateway behavior remains intact.
- CI passes on the implementation branch before merge.
