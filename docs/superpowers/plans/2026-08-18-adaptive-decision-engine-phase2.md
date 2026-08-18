# Adaptive Decision Engine Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade JARVIS from verified second-brain recall into an adaptive, auditable decision system that learns which strategies work without self-modifying code or policy.

**Architecture:** Add three focused SQLite-backed components: strategy memory, outcome feedback, and adaptive decision scoring. Integrate them through the existing second-brain/autonomous-learning boundary. Policy and ToolRegistry remain authoritative; learning can change ranking and confidence, never authority.

**Tech Stack:** Python 3.13, SQLite, dataclasses/enums, pytest, existing local Ollama/Termux runtime.

**Spec:** Approved PROJECT-NAS Phase 2 design in conversation.

## Global Constraints
- $0/local-first; no paid cloud AI/API dependency.
- No self-modifying source code or security policy.
- ToolRegistry/policy remains authoritative for capabilities and execution.
- Verified learning gates promotion of knowledge; outcomes may adjust strategy confidence only.
- Inputs remain bounded and deterministic.
- Existing GREEN certification must remain GREEN.

---

### Task 1: Strategy and outcome domain models
**Files:** Create `runtime/adaptive_decision.py`; Test `tests/test_adaptive_decision.py`.

**Interfaces:** `Strategy`, `StrategyOutcome`, `DecisionCandidate`, `DecisionScore`, enums for outcome status.

- [ ] Write failing tests for deterministic strategy identity, bounded fields, and outcome validation.
- [ ] Run focused tests and verify the expected failures.
- [ ] Implement minimal immutable dataclasses/enums.
- [ ] Run focused tests and verify they pass.

### Task 2: Strategy memory repository
**Files:** Create `runtime/strategy_memory.py`; Test `tests/test_strategy_memory.py`.

**Interfaces:** `record_strategy`, `record_outcome`, `list_strategies`, `strategy_stats`, `update_confidence`.

- [ ] Write failing tests for SQLite persistence, repeated outcomes, and confidence bounds.
- [ ] Run focused tests and verify failure.
- [ ] Implement bounded SQLite tables with deterministic aggregation.
- [ ] Ensure duplicate strategy observations do not corrupt evidence counts.
- [ ] Run focused tests and verify pass.

### Task 3: Adaptive decision scorer
**Files:** Modify `runtime/adaptive_decision.py`; Test `tests/test_adaptive_decision.py`.

**Interfaces:** `AdaptiveDecisionEngine.rank(candidates, context)`.

- [ ] Write failing tests showing successful strategies outrank weaker strategies while policy-denied candidates cannot become executable.
- [ ] Run focused tests and verify failure.
- [ ] Implement deterministic scoring using confidence, historical success rate, risk, and resource cost.
- [ ] Add stable tie-breaking so decisions are reproducible.
- [ ] Run focused tests and verify pass.

### Task 4: Outcome feedback loop
**Files:** Create `runtime/outcome_feedback.py`; Test `tests/test_outcome_feedback.py`.

**Interfaces:** `record`, `apply`, `strategy_effect`.

- [ ] Write failing tests for SUCCESS, FAILURE, PARTIAL, and UNKNOWN outcomes.
- [ ] Run focused tests and verify failure.
- [ ] Implement bounded confidence updates with conservative learning rates.
- [ ] Ensure UNKNOWN does not falsely reward or punish a strategy.
- [ ] Run focused tests and verify pass.

### Task 5: Second-brain integration
**Files:** Modify `runtime/second_brain.py`, `runtime/autonomous_learning.py`; Test `tests/test_second_brain_intelligence_v3.py`.

**Interfaces:** `recommend_strategy`, `record_outcome`, `strategy_history`.

- [ ] Write failing integration tests for recall → rank → outcome → improved ranking.
- [ ] Run focused tests and verify failure.
- [ ] Integrate strategy memory without bypassing cognitive-memory verification or orchestration policy.
- [ ] Preserve existing public interfaces.
- [ ] Run focused integration tests and verify pass.

### Task 6: Full verification and certification
- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m compileall -q runtime tests`.
- [ ] Run `python runtime/doctor.py`.
- [ ] Run `bash runtime/project-nas-certify.sh`.
- [ ] Confirm zero failures and GREEN certification.
- [ ] Review for paid dependencies, policy bypasses, unbounded input, and self-modifying behavior.
