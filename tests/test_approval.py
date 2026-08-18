import pytest

from runtime.approval import ApprovalManager, ApprovalRequired, action_fingerprint


def test_action_fingerprint_changes_with_payload():
    first = action_fingerprint("tool.x", "1", {"value": 1})
    second = action_fingerprint("tool.x", "1", {"value": 2})
    assert first != second


def test_approval_is_bound_to_exact_action_and_consumed_once():
    manager = ApprovalManager()
    proposal = manager.propose(
        tool_name="shell.exec",
        version="1",
        payload={"command": "echo hello"},
        risk="low",
        reason="execution requires approval",
    )

    receipt = manager.approve(proposal.proposal_id)
    assert manager.consume(receipt, proposal) is True
    assert manager.consume(receipt, proposal) is False


def test_mismatched_action_cannot_use_approval():
    manager = ApprovalManager()
    proposal = manager.propose(
        tool_name="shell.exec",
        version="1",
        payload={"command": "echo hello"},
        risk="low",
        reason="execution requires approval",
    )
    receipt = manager.approve(proposal.proposal_id)
    different = manager.propose(
        tool_name="shell.exec",
        version="1",
        payload={"command": "rm -rf /"},
        risk="critical",
        reason="different action",
    )

    assert manager.consume(receipt, different) is False


def test_unknown_proposal_cannot_be_approved():
    manager = ApprovalManager()
    with pytest.raises(ApprovalRequired):
        manager.require("missing-proposal")
