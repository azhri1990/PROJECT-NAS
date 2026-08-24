# GitHub Archive Inventory — 2026-08-24

## Purpose
Preserve an auditable record that the GitHub repository contains substantial project state outside `main`, so consolidation does not erase historical implementation.

## Canonical observation
`main` currently points to `ebde6ddcc53fb0668636f685e05b3c09ba294c6c`.

## Verified branch families requiring reconciliation

### BOB
- `bob/control-plane-v1`
- `bob/autopilot-governance-v1`
- `feat/project-bob-autonomous-orchestrator`
- `feat/project-bob-mobile-local-control`
- `fix/bob-android-worker-auth`
- `fix/bob-autopilot-pid-lock`

### JARVIS / learning
- `feat/learning-feedback-v1`
- `feat/learning-quality-v1`
- `feat/jarvis-capability-core`
- `feat/jarvis-cognitive-orchestrator`

### NAS / security / gateway
- `feat/nas-core-hardening`
- `fix/gateway-audit-hardening`
- `fix/gateway-todo-policy-boundary`
- `feat/omni-safe-local-v2`
- `feat/omni-device-ai-bridges-v1`

### Autopilot / certification / doctor
- `autopilot/runtime-certification-2026-08-18-v2`
- `autopilot/autonomous-learning-certification`
- `autopilot/cognitive-orchestrator-certification`
- `autopilot/doctor-v11-certification`
- `autopilot/policy-engine-certification`
- `feature/doctor-v9`
- `feature/doctor-v10`
- `feature/doctor-hardening`

### Historical preservation
- `backup/2026-08-20-nas-bob-jarvis`

## Classification
Branches are preserved as historical implementation sources. They are not assumed safe to merge wholesale. Diverged branches require file-level reconciliation and tests.

## Important constraint
The GitHub connector can inspect and modify the public repository, but it cannot prove whether unpushed files still exist on Nash's PC or Android/Termux environment. Local-only work remains `UNVERIFIED-LOCAL` until supplied/pushed.

## Preservation rule
No historical branch should be deleted as part of this consolidation unless explicitly authorized after the archive is verified.
