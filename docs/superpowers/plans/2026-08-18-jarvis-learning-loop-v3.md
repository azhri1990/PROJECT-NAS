# JARVIS Learning Loop v3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a bounded local learning loop that turns verified outcomes into measurable strategy and memory improvements.

**Architecture:** Add one coordinator around the existing cognitive-memory and adaptive-decision layers. Keep execution authority in orchestration policy; learning may only influence ranking, confidence, and evidence-backed memory.

**Tech Stack:** Python 3.13, SQLite, existing PROJECT-NAS runtime modules, pytest.

**Spec:** `docs/superpowers/specs/2026-08-18-jarvis-learning-loop-v3-design.md`

## Global Constraints
- $0 / local-first; no paid cloud AI/API dependency.
- UNKNOWN outcomes never become learning evidence.
- Learning cannot grant capabilities or rewrite policy/code.
- All inputs are bounded and provenance is retained.
- Existing doctor/certification gates remain authoritative.

---

### Task 1: Learning-loop contract tests

**Files:**
- Create: `tests/test_learning_loop_v3.py`

**Interfaces:**
- Consumes: `LearningLoopV3` public API defined by the tests.
- Produces: executable behavioral contract for later implementation.

- [ ] **Step 1: Write failing tests** for observation, outcome evaluation, UNKNOWN no-op, consolidation, and metrics.
- [ ] **Step 2: Run the new tests** and confirm they fail because `LearningLoopV3` does not exist.

### Task 2: Implement deterministic coordinator

**Files:**
- Create: `runtime/learning_loop_v3.py`
- Modify: `runtime/second_brain.py`

**Interfaces:**
- `LearningLoopV3.observe(task, strategy_id, context, source)` returns an observation id.
- `LearningLoopV3.record_outcome(observation_id, status, evidence=1, lesson=None)` returns a result record.
- `LearningLoopV3.consolidate(query, limit=20)` returns bounded cognitive memories.
- `LearningLoopV3.metrics()` returns deterministic counters/rates.

- [ ] **Step 1:** Implement SQLite tables for observations, outcomes, and lessons.
- [ ] **Step 2:** Reject invalid/oversized input and unknown observation ids.
- [ ] **Step 3:** Treat UNKNOWN as a no-op for learning statistics.
- [ ] **Step 4:** Feed SUCCESS/PARTIAL/FAILURE into existing `SecondBrain.record_outcome`.
- [ ] **Step 5:** Promote only verified lessons into cognitive memory; never auto-pin.
- [ ] **Step 6:** Consolidate duplicate lessons through the existing cognitive-memory store.
- [ ] **Step 7:** Expose bounded metrics without exposing security authority.

### Task 3: Integration and verification

**Files:**
- Modify: `tests/test_learning_loop_v3.py`

- [ ] Run the focused learning-loop tests.
- [ ] Run the full pytest suite.
- [ ] Run Python compilation.
- [ ] Run `runtime/doctor.py`.
- [ ] Run `runtime/project-nas-certify.sh`.
- [ ] Review the final diff for security-boundary regressions.
