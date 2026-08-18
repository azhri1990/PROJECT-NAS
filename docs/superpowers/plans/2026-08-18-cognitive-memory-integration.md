# Cognitive Memory Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing verified learning primitives into a controlled, inspectable cognitive-memory lifecycle without weakening policy/tool boundaries.

**Architecture:** Add a focused cognitive-memory module above the existing SQLite autonomous learning store. It will model provenance, lifecycle state, confidence, recency, and contradiction relationships, while delegating promotion decisions to the existing verified-learning engine. Existing orchestration and security policy remain authoritative.

**Tech Stack:** Python 3.13, SQLite, dataclasses/enums, pytest; no new runtime dependencies.

**Spec:** Approved Second-Brain Intelligence v2 / Cognitive Memory Integration design from the PROJECT-NAS build conversation.

## Global Constraints

- Zero-cost: no paid cloud AI/API dependency.
- Local-first: existing SQLite/Ollama runtime remains the source of local intelligence.
- Security boundary: learning cannot modify policy or grant capabilities.
- Evidence-first: unverified or contradicted knowledge is never promoted.
- Regression safety: preserve the existing 190-test GREEN baseline.

---

### Task 1: Cognitive memory contract

**Files:**
- Create: `runtime/cognitive_memory.py`
- Test: `tests/test_cognitive_memory.py`

**Interfaces:**
- Produces: `MemoryLifecycle`, `MemoryProvenance`, `CognitiveMemory`, `CognitiveMemoryStore`.

- [ ] Write failing tests for lifecycle values, provenance validation, and deterministic IDs.
- [ ] Run the focused tests and confirm failure.
- [ ] Implement the minimal dataclasses/enums and SQLite schema.
- [ ] Run focused tests and confirm pass.
- [ ] Commit the contract.

### Task 2: Evidence-aware lifecycle

**Files:**
- Modify: `runtime/cognitive_memory.py`
- Modify: `tests/test_cognitive_memory.py`

**Interfaces:**
- Produces: `promote_verified`, `mark_conflicted`, `revalidate`, `record_evidence`.

- [ ] Add tests for NEW → VERIFIED → TRUSTED transitions.
- [ ] Add tests proving contradictory evidence produces CONFLICTED state.
- [ ] Add tests proving policy learning cannot enter TRUSTED automatically.
- [ ] Implement lifecycle transitions.
- [ ] Run focused tests and full regression suite.
- [ ] Commit.

### Task 3: Evidence-weighted recall and provenance

**Files:**
- Modify: `runtime/cognitive_memory.py`
- Modify: `tests/test_cognitive_memory.py`

**Interfaces:**
- Produces: `recall(query, limit)` returning deterministic ranked `CognitiveMemory` records.

- [ ] Add tests for relevance + confidence + evidence + freshness ordering.
- [ ] Add provenance preservation tests.
- [ ] Implement deterministic ranking without an external vector database dependency.
- [ ] Run focused tests and full regression suite.
- [ ] Commit.

### Task 4: Integrate with autonomous learning

**Files:**
- Modify: `runtime/autonomous_learning.py`
- Modify: `tests/test_second_brain_intelligence_v2.py`

- [ ] Add integration tests showing promoted learning receives cognitive-memory metadata.
- [ ] Implement the narrow adapter; keep existing public learning behaviour compatible.
- [ ] Run full regression suite.
- [ ] Commit.

### Task 5: Certification and auditability

**Files:**
- Modify: certification/runtime checks only if required by existing gate conventions.
- Test: `tests/test_cognitive_memory.py`

- [ ] Add certification coverage for lifecycle integrity and protected-policy behaviour.
- [ ] Run compileall, doctor, recovery simulation, and full pytest suite.
- [ ] Require CERTIFICATION: GREEN before merge.
- [ ] Commit and open PR for review.
