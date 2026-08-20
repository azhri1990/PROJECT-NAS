from runtime.policy import Capability, PolicyEngine, RiskLevel, ToolRequest


def test_unknown_or_high_risk_actions_fail_closed():
    engine = PolicyEngine()
    request = ToolRequest(
        tool_name="unknown_tool",
        capability=Capability.EXECUTE_PROCESS,
        risk=RiskLevel.HIGH,
        input={},
    )
    decision = engine.evaluate(request)
    assert decision.allowed is False


def test_repository_writes_are_not_implicitly_allowed():
    engine = PolicyEngine()
    request = ToolRequest(
        tool_name="write_file",
        capability=Capability.WRITE_REPOSITORY,
        risk=RiskLevel.MEDIUM,
        input={"path": "README.md"},
    )
    decision = engine.evaluate(request)
    assert decision.allowed is False


def test_low_risk_read_only_action_is_allowed():
    engine = PolicyEngine()
    request = ToolRequest(
        tool_name="read_file",
        capability=Capability.READ_REPOSITORY,
        risk=RiskLevel.LOW,
        input={"path": "README.md"},
    )
    decision = engine.evaluate(request)
    assert decision.allowed is True


def test_network_access_is_denied_by_default():
    engine = PolicyEngine()
    request = ToolRequest(
        tool_name="http_request",
        capability=Capability.NETWORK_ACCESS,
        risk=RiskLevel.LOW,
        input={"url": "https://example.invalid"},
    )
    decision = engine.evaluate(request)
    assert decision.allowed is False
