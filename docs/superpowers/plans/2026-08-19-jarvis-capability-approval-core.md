# JARVIS Capability Approval Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give JARVIS a capability/proposal/approval control plane where consequential execution is bound to one explicit Nash approval and cannot be reused for another action.

**Architecture:** Keep the existing PolicyEngine authoritative. Add an in-process ApprovalManager that fingerprints the exact tool, version, payload and policy risk, creates an auditable proposal, and issues a one-shot approval receipt. ToolRegistry will require and consume that receipt only when policy returns REQUIRE_CONFIRMATION; read-only ALLOW behavior remains unchanged.

**Tech Stack:** Python 3, dataclasses, stdlib hashlib/json/uuid, pytest.

**Spec:** JARVIS Capability & Approval Core design agreed in conversation.

## Global Constraints

- $0/local-first; no required paid cloud AI/API subscription.
- Nash approval remains the authority for consequential execution.
- Approval is action-specific, one-shot, and cannot authorize a different payload/tool/version.
- Policy changes require Nash approval and are never inferred from learning or memory.
- Memory, learning, confidence, and recommendations never grant execution authority.
- Existing regression behavior must remain green unless intentionally superseded by the approval contract.

---

### Task 1: Define approval contracts

**Files:**
- Create: `runtime/approval.py`
- Test: `tests/test_approval.py`

- [ ] Write tests for deterministic action fingerprints, proposal creation, exact-action approval, rejection of mismatched actions, and one-shot consumption.
- [ ] Run the new tests and verify they fail because the approval module does not yet exist.
- [ ] Implement `ActionProposal`, `ApprovalReceipt`, `ApprovalManager`, and `ApprovalRequired` using only the Python standard library.
- [ ] Run approval tests and verify green.

### Task 2: Integrate approval with ToolRegistry

**Files:**
- Modify: `runtime/orchestration_tools.py`
- Test: `tests/test_orchestration_tools.py`

- [ ] Add tests proving a confirmation-gated tool cannot execute without approval.
- [ ] Add tests proving the exact approved payload executes once.
- [ ] Add tests proving the same receipt cannot be replayed or used for a different payload/tool.
- [ ] Preserve existing read-only ALLOW behavior.
- [ ] Implement the smallest registry integration that checks policy first, creates an approval proposal when required, and consumes a valid receipt before invoking the handler.
- [ ] Run targeted tests and then the full suite.

### Task 3: Expose proposals through CognitiveOrchestrator

**Files:**
- Modify: `runtime/cognitive_orchestrator.py`
- Test: `tests/test_cognitive_orchestrator.py`

- [ ] Add a test that a gated action returns an approval-required result without executing the handler.
- [ ] Add a test that an approved receipt permits exactly that action.
- [ ] Keep memory as context only and learning as non-authoritative.
- [ ] Implement proposal/approval plumbing without allowing the model or memory to self-approve.
- [ ] Run targeted and full tests.

### Task 4: Add recommendation metadata

**Files:**
- Create: `runtime/recommendations.py`
- Test: `tests/test_recommendations.py`

- [ ] Add tests for structured recommendation text, reason, risk, expected benefit, and alternatives.
- [ ] Ensure recommendation objects have no approval or execution authority fields that can be interpreted as permission.
- [ ] Implement a small deterministic recommendation contract suitable for future generators/adapters.
- [ ] Run the full suite.

### Task 5: Documentation and verification

**Files:**
- Modify: `runtime/approval.py` or `docs/` only if verification reveals documentation gaps.

- [ ] Run `python -m pytest -q`.
- [ ] Run `git diff --check`.
- [ ] Inspect the final diff for authority bypasses.
- [ ] Commit the completed batch with a security-focused message.
- [ ] Push the branch and report the exact commit plus any remaining limitations.
