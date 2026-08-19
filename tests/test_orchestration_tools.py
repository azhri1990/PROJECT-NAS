import pytest

from runtime.approval import ApprovalManager, ApprovalRequired
from runtime.orchestration_policy import Capability
from runtime.orchestration_tools import ToolRegistry, ToolSpec


def gated_registry(manager):
    registry = ToolRegistry(approval=manager)
    registry.register(
        ToolSpec(
            name="shell.exec",
            capability=Capability.EXECUTE_SAFE,
            risk="low",
            input_schema={"type": "object", "additionalProperties": False},
            handler=lambda payload: {"executed": payload["command"]},
        )
    )
    return registry


def test_confirmation_gated_tool_proposes_without_executing():
    manager = ApprovalManager()
    registry = gated_registry(manager)

    with pytest.raises(ApprovalRequired) as exc:
        registry.execute("shell.exec", {"command": "echo hello"})

    proposal = manager.require(exc.value.proposal_id)
    assert proposal.tool_name == "shell.exec"
    assert proposal.payload == {"command": "echo hello"}


def test_exact_approval_allows_one_execution():
    manager = ApprovalManager()
    registry = gated_registry(manager)

    with pytest.raises(ApprovalRequired) as exc:
        registry.execute("shell.exec", {"command": "echo hello"})

    proposal = manager.require(exc.value.proposal_id)
    receipt = manager.approve(proposal.proposal_id)

    assert registry.execute("shell.exec", {"command": "echo hello"}, approval=receipt) == {
        "executed": "echo hello"
    }


def test_approval_cannot_be_replayed_or_retargeted():
    manager = ApprovalManager()
    registry = gated_registry(manager)

    with pytest.raises(ApprovalRequired) as first:
        registry.execute("shell.exec", {"command": "echo hello"})
    first_proposal = manager.require(first.value.proposal_id)
    receipt = manager.approve(first_proposal.proposal_id)

    assert registry.execute("shell.exec", {"command": "echo hello"}, approval=receipt)
    with pytest.raises(PermissionError):
        registry.execute("shell.exec", {"command": "echo hello"}, approval=receipt)

    with pytest.raises(ApprovalRequired) as second:
        registry.execute("shell.exec", {"command": "echo safe"})
    assert second.value.proposal_id != first_proposal.proposal_id
