from runtime.policy import Capability, PolicyEngine, RiskLevel, ToolRequest


def test_read_repository_is_allowed_for_low_risk_request():
    request = ToolRequest(
        tool_name="repo.progress",
        capability=Capability.READ_REPOSITORY,
        risk=RiskLevel.LOW,
        input={},
    )
    decision = PolicyEngine().evaluate(request)
    assert decision.allowed is True


def test_process_execution_is_denied_by_default():
    request = ToolRequest(
        tool_name="shell.run",
        capability=Capability.EXECUTE_PROCESS,
        risk=RiskLevel.CRITICAL,
        input={"command": "whoami"},
    )
    decision = PolicyEngine().evaluate(request)
    assert decision.allowed is False
    assert "execute_process" in decision.reason


def test_write_requires_explicit_approval():
    request = ToolRequest(
        tool_name="repo.write",
        capability=Capability.WRITE_REPOSITORY,
        risk=RiskLevel.HIGH,
        input={"path": "x.txt"},
    )
    decision = PolicyEngine().evaluate(request)
    assert decision.allowed is False
    assert "approval" in decision.reason
