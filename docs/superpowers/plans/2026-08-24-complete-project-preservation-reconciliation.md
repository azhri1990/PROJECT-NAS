# Complete PROJECT-NAS Preservation & Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish an evidence-backed GitHub archive of PROJECT-NAS, PROJECT-BOB, and JARVIS so every GitHub-hosted implementation is preserved and every unresolved local-only item is explicitly identified before canonical consolidation.

**Architecture:** Preserve existing branches as immutable historical sources; maintain a machine-readable implementation matrix in `docs/AUDITS/`; reconcile shared runtime/security files by comparing branch commits against `main`; never wholesale-merge divergent branches. Canonical adoption occurs only after file-level review and verification.

**Tech Stack:** Git/GitHub, Python runtime, pytest, FastAPI/Flask runtime components, GitHub Actions, Markdown audit artifacts.

**Spec:** `docs/PROJECT-MASTER-STATE-2026-08-24.md` and `docs/RULES/PROJECT-RULES-v1.md`

## Global Constraints

- GitHub is the canonical project repository.
- Historical branches must not be deleted during preservation.
- Do not claim unpushed PC/Android/Termux work is synchronized without evidence.
- Secrets, credentials, private keys, and tokens must never be committed.
- Consequential execution must fail closed when authorization or policy is unavailable.
- Memory, learning, recommendations, and capability metadata cannot grant execution authority.
- Exact consequential actions must remain approval-bound where approval is required.
- Verify implementation with relevant tests before declaring canonical completion.
- Preserve Android/Termux compatibility where the project explicitly supports it.

---

### Task 1: Freeze and inventory GitHub preservation sources

**Files:**
- Modify: `docs/AUDITS/GITHUB-ARCHIVE-INVENTORY-2026-08-24.md`
- Modify: `docs/ARCHIVE/IMPLEMENTATION-MATRIX.md`

**Interfaces:**
- Consumes: GitHub branch/PR refs.
- Produces: explicit preservation classification for every identified implementation family.

- [ ] **Step 1: Enumerate all repository branches and major PR heads.**

- [ ] **Step 2: Record each branch's relationship to `main` and its subsystem family.**

- [ ] **Step 3: Mark each family `PRESERVED`, `RECONCILE`, `CANONICAL`, or `UNVERIFIED-LOCAL`.**

- [ ] **Step 4: Commit the updated inventory.**

---

### Task 2: Capture BOB implementation deltas

**Files:**
- Modify: `docs/AUDITS/PR-IMPLEMENTATION-RECONCILIATION-2026-08-24.md`
- Modify: `docs/ARCHIVE/IMPLEMENTATION-MATRIX.md`

**Interfaces:**
- Consumes: `bob/control-plane-v1`, `bob/autopilot-governance-v1`, `feat/project-bob-autonomous-orchestrator`, mobile-control branches.
- Produces: source-of-truth mapping for BOB control loop, workers, queue, watchdog, resilience, governance, learning, autopilot and command channel.

- [ ] **Step 1: Compare each BOB branch against `main`.**

- [ ] **Step 2: Identify shared files with divergent implementations.**

- [ ] **Step 3: Record unique files and behavior without copying conflicting source into `main`.**

- [ ] **Step 4: Identify tests and verification contracts associated with each implementation.**

- [ ] **Step 5: Commit the BOB reconciliation record.**

---

### Task 3: Capture JARVIS implementation deltas

**Files:**
- Modify: `docs/AUDITS/PR-IMPLEMENTATION-RECONCILIATION-2026-08-24.md`
- Modify: `docs/ARCHIVE/IMPLEMENTATION-MATRIX.md`

**Interfaces:**
- Consumes: JARVIS capability/approval, learning-feedback, and learning-quality branches.
- Produces: source mapping for approval receipts, action fingerprints, capability metadata, recommendations, learning feedback, quality calibration, and orchestration integration.

- [ ] **Step 1: Compare JARVIS branches against `main`.**

- [ ] **Step 2: Identify security-sensitive shared files.**

- [ ] **Step 3: Record exact approval/authority invariants that must survive reconciliation.**

- [ ] **Step 4: Record tests proving those invariants.**

- [ ] **Step 5: Commit the JARVIS reconciliation record.**

---

### Task 4: Capture NAS, gateway, routing, and Omni deltas

**Files:**
- Modify: `docs/AUDITS/IMPLEMENTATION-FAMILY-DELTA-2026-08-24.md`
- Modify: `docs/AUDITS/IMPLEMENTATION-FAMILY-DELTA-2026-08-24-B.md`

**Interfaces:**
- Consumes: NAS hardening, gateway hardening/policy, Omni-safe-local, Omni-device bridge, and model-router branches.
- Produces: file-level preservation map for memory, audit, gateway, policy, provider, model routing, and security behavior.

- [ ] **Step 1: Compare each branch against current `main`.**

- [ ] **Step 2: Separate historical-only changes from still-unique changes.**

- [ ] **Step 3: Flag changes affecting authorization, tool execution, provider routing, or memory integrity for mandatory review.**

- [ ] **Step 4: Record associated regression tests and CI contracts.**

- [ ] **Step 5: Commit the updated delta records.**

---

### Task 5: Capture certification and diagnostics history

**Files:**
- Modify: `docs/AUDITS/IMPLEMENTATION-FAMILY-DELTA-2026-08-24.md`
- Create: `docs/AUDITS/CERTIFICATION-HISTORY-2026-08-24.md`

**Interfaces:**
- Consumes: autopilot certification, runtime certification, Termux hardening, doctor and diagnostic branches.
- Produces: auditable map of certification evidence and historical diagnostic implementations.

- [ ] **Step 1: Compare certification branches against `main`.**

- [ ] **Step 2: Record unique certification workflows, scripts, and tests.**

- [ ] **Step 3: Preserve branches that are behind `main` as historical evidence.**

- [ ] **Step 4: Record which certification evidence is current versus historical.**

- [ ] **Step 5: Commit certification history.**

---

### Task 6: Reconcile local PC and Android/Termux state

**Files:**
- Modify: `docs/AUDITS/LOCAL-STATE-RECONCILIATION-2026-08-24.md`

**Interfaces:**
- Consumes: user-supplied/pushed local repository state from PC and Android/Termux.
- Produces: verified GitHub commit/working-tree mapping and explicit unverified list.

- [ ] **Step 1: Obtain current local `git status`, branch, and commit SHA for PC.**

- [ ] **Step 2: Obtain current local `git status`, branch, and commit SHA for Android/Termux.**

- [ ] **Step 3: Push unpushed commits after confirming they contain no secrets.**

- [ ] **Step 4: Preserve uncommitted changes as a separate patch/artifact only after inspection.**

- [ ] **Step 5: Record the exact local-to-GitHub mapping.**

---

### Task 7: Produce final completeness audit

**Files:**
- Create: `docs/AUDITS/PROJECT-COMPLETENESS-AUDIT-2026-08-24.md`
- Modify: `docs/PROJECT-MASTER-STATE-2026-08-24.md`

**Interfaces:**
- Consumes: all branch, PR, implementation-family, certification, and local-state audit records.
- Produces: evidence-backed completeness classification.

- [ ] **Step 1: Count all preservation sources.**

- [ ] **Step 2: Confirm every identified implementation family has a GitHub source.**

- [ ] **Step 3: List every unresolved local-only artifact.**

- [ ] **Step 4: Classify completeness as COMPLETE, COMPLETE-GITHUB-BUT-LOCAL-UNVERIFIED, or INCOMPLETE.**

- [ ] **Step 5: Commit the final audit.**

---

### Task 8: Canonical consolidation only after completeness

**Files:**
- Modify: affected runtime/security files only after Tasks 1-7 pass.
- Modify: `docs/ARCHIVE/IMPLEMENTATION-MATRIX.md`

**Interfaces:**
- Consumes: verified implementation matrix and test evidence.
- Produces: one canonical implementation with preserved historical sources.

- [ ] **Step 1: Select one implementation for each reconciled subsystem.**

- [ ] **Step 2: Write failing regression tests for every security/authority invariant that must survive.**

- [ ] **Step 3: Implement the minimal canonical reconciliation.**

- [ ] **Step 4: Run targeted tests.**

- [ ] **Step 5: Run the full relevant test suite and diagnostics.**

- [ ] **Step 6: Record the final decision and evidence.**

- [ ] **Step 7: Merge only verified canonical changes.**

