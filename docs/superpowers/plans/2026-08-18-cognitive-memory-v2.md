# Cognitive Memory V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade JARVIS/PROJECT-NAS cognitive memory into a stronger, auditable second-brain layer with confidence, provenance, contradiction handling, decay, consolidation, knowledge-gap detection, and rollback without adding cost or self-modifying policy.

**Architecture:** Extend the existing SQLite-backed `CognitiveMemoryStore` as the authoritative lifecycle store. Add an append-only local history table for rollback/audit, deterministic contradiction and gap analysis, and a small second-brain facade that exposes these capabilities to autonomous learning while preserving existing interfaces and behavior. Trusted automatic promotion remains compatible; user-approved permanent knowledge is represented separately so approval is explicit and auditable.

**Tech Stack:** Python 3.13, SQLite, dataclasses/enums, pytest, existing PROJECT-NAS local Ollama/Termux runtime.

**Spec:** Existing approved Cognitive Memory V2 design in conversation; this plan operationalizes the approved requirements.

## Global Constraints
- $0/local-first; no paid cloud AI/API dependency.
- No self-modifying code or policy.
- ToolRegistry/policy remains authoritative for capabilities and execution.
- Learning promotion remains verification-gated.
- Memory inputs and limits remain bounded.
- Certification must remain GREEN after implementation.

---

### Task 1: Memory lifecycle audit/history
**Files:** Modify `runtime/cognitive_memory.py`; Test `tests/test_cognitive_memory_v2.py`.

**Interfaces:** `MemoryLifecycle.PINNED`; `approve_pinned(memory_id, approver="user")`; `history(memory_id)`; `rollback(memory_id)`.

- [ ] Write failing tests for pinned approval, history creation, and rollback.
- [ ] Run focused tests and confirm the new behaviors fail.
- [ ] Add the smallest SQLite history schema and lifecycle methods.
- [ ] Run focused tests and confirm they pass.

### Task 2: Deterministic contradiction and consolidation intelligence
**Files:** Modify `runtime/cognitive_memory.py`; Test `tests/test_cognitive_memory_v2.py`.

**Interfaces:** `find_contradictions(statement, kind=None)`; `consolidate(statement, kind)`; `review()`.

- [ ] Write failing tests for polarity contradiction detection and evidence consolidation.
- [ ] Run focused tests and confirm failure.
- [ ] Implement deterministic token/polarity comparison using the standard library.
- [ ] Preserve strongest confidence and aggregate repeated evidence exactly once per observation.
- [ ] Run focused tests and confirm pass.

### Task 3: Knowledge-gap detection and second-brain facade
**Files:** Modify `runtime/second_brain.py`; Test `tests/test_second_brain_intelligence_v2.py`.

**Interfaces:** `knowledge_gaps(queries)`; `approve_permanent(memory_id, approver="user")`; `memory_history(memory_id)`; `rollback_memory(memory_id)`.

- [ ] Write failing tests for gap detection, permanent approval, history exposure, and rollback.
- [ ] Run focused tests and confirm failure.
- [ ] Delegate directly to the cognitive store without bypassing verification.
- [ ] Keep invalid/empty queries bounded and rejected.
- [ ] Run focused tests and confirm pass.

### Task 4: Autonomous learning integration
**Files:** Modify `runtime/autonomous_learning.py`; Test `tests/test_autonomous_learning_v2.py`.

**Interfaces:** Preserve existing `learn`, `recall`, `recall_cognitive`, `revalidate`, and `consolidate` compatibility. Never convert unverified or contradicted candidates into pinned knowledge.

- [ ] Write failing integration tests for review results and blocked permanent promotion.
- [ ] Run focused tests and confirm failure.
- [ ] Implement minimal delegation and lifecycle checks.
- [ ] Run focused integration tests and confirm pass.

### Task 5: Full verification and certification
- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m compileall -q runtime tests`.
- [ ] Run `python runtime/doctor.py`.
- [ ] Run `bash runtime/project-nas-certify.sh`.
- [ ] Confirm certification remains GREEN and test count does not regress.
- [ ] Review for accidental dependencies, policy bypasses, unbounded inputs, or self-modifying behavior.

**Ruling:** Preserve existing automatic TRUSTED promotion for verified high-support facts to avoid breaking callers. Add PINNED as the explicit user-approved permanent layer instead of redefining TRUSTED.
