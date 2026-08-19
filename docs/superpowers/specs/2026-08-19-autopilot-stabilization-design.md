# PROJECT-NAS AUTO PILOT Stabilization Design

## Goal
Restore a verified PROJECT-NAS baseline before adding PROJECT-BOB, with the builder layer treated as a governed subsystem rather than an unrestricted self-modifying agent.

## Scope
This phase addresses the repository's current verification gate and the three known risk areas: orchestration contracts, Windows-compatible runtime execution, and SQLite concurrency. PROJECT-BOB implementation is a separate phase after this baseline is green.

## Architecture
1. Preserve the existing capability/policy boundary as authoritative; cognitive memory and learning remain non-authoritative context.
2. Make persistence operations resilient to short SQLite contention using bounded connection settings and transactional writes, without changing the database schema unnecessarily.
3. Keep platform-specific execution behind existing runtime wrappers and provide deterministic Windows behavior rather than assuming POSIX shell semantics.
4. Add regression tests before each behavioral change and use GitHub Actions as the reproducible Linux verification gate. Local Windows/Termux verification remains required when the user runs the repository locally.

## Security constraints
- Local-first and $0 software architecture remain mandatory.
- No learning result may grant capabilities, modify policy, or mutate source code automatically.
- Unknown verification results fail closed.
- System mutation and external network capabilities remain denied or confirmation-gated by policy.
- Database inputs remain bounded.
- No secrets, tokens, or machine-specific paths are committed.

## Success criteria
- Full pytest suite passes in CI.
- Python compilation and shell syntax checks pass.
- PROJECT-NAS doctor passes in offline mode.
- No regression weakens the policy/verification boundary.
- The repository contains a documented, testable handoff point for PROJECT-BOB.
