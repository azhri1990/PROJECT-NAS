# AI Transfer Package

## Mission
Continue PROJECT-NAS as a long-lived personal OS platform containing PROJECT-NAS core, PROJECT-BOB worker/autopilot infrastructure, and JARVIS cognition/orchestration.

## Required behaviour for a successor AI

1. Read the repository before making claims about current state.
2. Treat GitHub as the canonical source of implementation state.
3. Read `docs/PROJECT-MASTER-STATE-2026-08-24.md`, `docs/PROJECT-FORENSIC-LEDGER.md`, and `docs/RULES/PROJECT-RULES-v1.md` before changing architecture or governance.
4. Distinguish verified repository state from local reports and historical conversation context.
5. Do not silently weaken authorization, policy, approval, or security boundaries.
6. Preserve compatibility with Android/Termux where the project explicitly supports it.
7. Verify changes with appropriate tests/diagnostics before declaring completion.
8. Document consequential architecture decisions and unresolved blockers.

## Architecture shorthand

`BOB -> NAS -> JARVIS` is the intended control relationship: BOB provides workers/control-plane execution infrastructure; NAS provides the governed platform, policy, tools, memory and runtime foundations; JARVIS provides bounded cognition/orchestration above those controls.

## Zero-cost/local-first direction

The project has been designed around local/self-hosted/open-source AI where practical, including Ollama and mobile SQLite fallback. Avoid introducing paid external AI dependencies unless explicitly authorized as a project change.

## Authority invariant

AI cognition is not authority. Learning is not authority. Memory is not authority. Capability metadata is not authority. Recommendations are not authority. Consequential execution remains subject to policy and the applicable approval boundary.

## Handover requirement

If a fact cannot be verified from the repository, label it as unverified rather than silently converting it into canonical state.
