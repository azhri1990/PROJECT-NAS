# BOB PR Consolidation

## Current policy

BOB work is consolidated into the current mainline and the approved control-plane PR rather than continuing parallel stale branches.

## PR disposition

- PR #29 (`feat/project-bob-autonomous-orchestrator`) is stale: its autonomous orchestrator work is already present on `main`, while the branch is based on an older revision and is not mergeable.
- PR #36 (`bob/autopilot-governance-v1`) remains a separate governance/security change and must be reviewed independently before merge.
- PR #37 (`bob/control-plane-v1`) is the current control-plane integration branch.

## Rule

New BOB features should target the current integration line. Do not revive stale branches merely to preserve historical implementation work. Before closing a branch, verify that its unique required behavior is already present or explicitly migrated.
