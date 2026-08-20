from runtime.autopilot_governance import AutopilotGovernance, DecisionClass
from runtime.policy import Capability, PolicyEngine, RiskLevel, ToolRequest


def test_nas_policy_is_an_independent_gate():
    governance = AutopilotGovernance(PolicyEngine())
    request = ToolRequest(
        tool_name="write_file",
        capability=Capability.WRITE_REPOSITORY,
        risk=RiskLevel.MEDIUM,
        input={"path": "README.md"},
    )
    decision = governance.classify(request)
    assert decision.classification is DecisionClass.ESCALATE
    assert "NAS policy denied" in decision.reason


def test_low_risk_read_is_automatic_when_nas_allows_it():
    decision = AutopilotGovernance().classify(
        ToolRequest(
            tool_name="read_file",
            capability=Capability.READ_REPOSITORY,
            risk=RiskLevel.LOW,
            input={"path": "README.md"},
        )
    )
    assert decision.classification is DecisionClass.AUTO


def test_process_and_network_are_escalated_even_if_labeled_low_risk():
    governance = AutopilotGovernance()
    for capability in (Capability.EXECUTE_PROCESS, Capability.NETWORK_ACCESS):
        decision = governance.classify(
            ToolRequest("test", capability, RiskLevel.LOW, {})
        )
        assert decision.classification is DecisionClass.ESCALATE


def test_high_and_critical_risk_require_nash():
    governance = AutopilotGovernance()
    for risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        decision = governance.classify(
            ToolRequest("read_file", Capability.READ_REPOSITORY, risk, {})
        )
        assert decision.classification is DecisionClass.ESCALATE
