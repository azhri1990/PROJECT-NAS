# PR Implementation Reconciliation — 2026-08-24

## Scope
Compared the three principal open BOB/JARVIS PR payloads against the repository baseline for preservation planning.

## PR #37 — BOB control plane
Preserve and reconcile the BOB autopilot/control-plane family, including daemon/loop/runner, tasks, verification, learning, control loop, persistent queue, resilience, watchdog, worker, and associated tests/tooling.

## PR #36 — BOB Autopilot Governance v1
Preserve and reconcile governance, risk classification, escalation, resilience, watchdog, persistent worker, failure ledger, control loop, specifications, implementation plan, and CI verification contracts.

## PR #25 — JARVIS capability/action approval core
Preserve and reconcile approval receipts, exact action/tool/version/payload binding, capability metadata, recommendation/learning plumbing, orchestration integration, and security regression tests.

## Decision
Do NOT wholesale-merge these PRs. The payloads overlap in BOB control-plane/runtime responsibilities and modify security-sensitive execution boundaries. They require file-level and test-level reconciliation.

## Preservation status
All three remain preserved by their GitHub PR branches. This document records their unique implementation families so that future consolidation can be performed without losing historical code.

## Local-only boundary
Any unpushed PC/Android/Termux changes remain unverified until directly reconciled from the local working trees.
