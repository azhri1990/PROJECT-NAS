# PROJECT-NAS Master State

**Date:** 2026-08-24
**Purpose:** Canonical source-of-truth index for PROJECT-NAS, PROJECT-BOB, and JARVIS.

## 1. Scope

This repository is intended to contain the implementation, data, rules, tests, architecture, operational knowledge, historical decisions, and transfer context required to understand and continue the project without relying on chat memory.

## 2. Systems

### PROJECT-NAS
Personal OS / platform layer. Current repository contains the core runtime, policy engine, memory layer, local-model layer, diagnostics, tests, and development/runtime dependency definitions.

Canonical local runtime documented by README:
- Ollama: `http://127.0.0.1:11434`
- Memory API: `http://127.0.0.1:5000`
- Default model: `llama3.2:3b`
- Mobile/Termux runtime uses the SQLite memory adapter.

### PROJECT-BOB
Worker/control-plane/autopilot system operating across Android/Termux, PC, and tablet workers. GitHub currently contains branches for the BOB control plane and autopilot governance work.

### JARVIS
AI cognition/orchestration layer covering memory, learning, recommendations, capability metadata, approvals, and bounded consequential execution. GitHub currently contains an open draft PR for the capability and action-approval core.

## 3. Current GitHub state

Default branch: `main`.

Relevant open draft PRs observed on 2026-08-24:
- PR #25 — `feat: build JARVIS capability and action approval core` — head `feat/learning-feedback-v1`.
- PR #36 — `BOB Autopilot Governance v1` — head `bob/autopilot-governance-v1`.
- PR #37 — `feat: build BOB control plane` — head `bob/control-plane-v1`.

These are documented as branches/PRs, not assumed to be part of `main` until verified and merged.

## 4. Important known gap

Chat history contains additional project knowledge and reports of local-only work. GitHub cannot be treated as complete until those local changes are reconciled against the repository. In particular, previously reported Windows SQLite file-lock failures and subsequent local fixes require repository-level verification.

## 5. Canonical-source rule

A project capability is considered canonical only when its implementation/data is committed to GitHub, its governing rules are documented, and its verification evidence is recorded. Chat discussion may inform the project but is not itself the canonical artifact.

## 6. Security boundary

Secrets, passwords, private keys, access tokens, and other credentials must never be committed to this repository. They must be handled through appropriate secret storage or local configuration.
