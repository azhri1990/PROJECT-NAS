import pytest

from runtime.omni.policy import (
    ActionRisk,
    Capability,
    PolicyDecision,
    PolicyEngine,
    PolicyRequest,
)


def test_health_and_chat_are_allowed_by_default():
    engine = PolicyEngine()
    for capability in (Capability.PROVIDER_HEALTH, Capability.PROVIDER_CHAT):
        decision = engine.evaluate(
            PolicyRequest(action=capability.value, capability=capability, risk=ActionRisk.LOW)
        )
        assert decision == PolicyDecision.allow("local-first provider capability")


def test_device_control_is_denied_without_explicit_approval():
    engine = PolicyEngine()
    decision = engine.evaluate(
        PolicyRequest(
            action="terminal",
            capability=Capability.DEVICE_CONTROL,
            risk=ActionRisk.HIGH,
            human_approved=False,
        )
    )
    assert decision.allowed is False
    assert decision.reason == "human approval required"


def test_device_control_can_be_allowed_only_with_approval():
    engine = PolicyEngine()
    decision = engine.evaluate(
        PolicyRequest(
            action="terminal",
            capability=Capability.DEVICE_CONTROL,
            risk=ActionRisk.HIGH,
            human_approved=True,
        )
    )
    assert decision.allowed is True


def test_unknown_capability_is_rejected():
    engine = PolicyEngine()
    with pytest.raises(ValueError):
        PolicyRequest(action="x", capability="not-a-capability", risk=ActionRisk.LOW)
