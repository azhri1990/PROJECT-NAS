from runtime.autopilot_governance import AutopilotGovernance, DecisionClass
from runtime.policy import Capability, RiskLevel, ToolRequest


def request(capability: Capability, risk: RiskLevel) -> ToolRequest:
    return ToolRequest("test", capability, risk, {})


def test_low_risk_read_is_automatic():
    decision = AutopilotGovernance().classify(
        request(Capability.READ_REPOSITORY, RiskLevel.LOW)
    )
    assert decision.classification is DecisionClass.AUTO


def test_write_requires_nash():
    decision = AutopilotGovernance().classify(
        request(Capability.WRITE_REPOSITORY, RiskLevel.MEDIUM)
    )
    assert decision.classification is DecisionClass.ESCALATE


def test_execution_requires_nash_even_when_low_risk_label_is_supplied():
    decision = AutopilotGovernance().classify(
        request(Capability.EXECUTE_PROCESS, RiskLevel.LOW)
    )
    assert decision.classification is DecisionClass.ESCALATE


def test_network_requires_nash_even_when_low_risk_label_is_supplied():
    decision = AutopilotGovernance().classify(
        request(Capability.NETWORK_ACCESS, RiskLevel.LOW)
    )
    assert decision.classification is DecisionClass.ESCALATE


def test_high_and_critical_risk_require_nash():
    governance = AutopilotGovernance()
    for risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        decision = governance.classify(request(Capability.READ_REPOSITORY, risk))
        assert decision.classification is DecisionClass.ESCALATE
