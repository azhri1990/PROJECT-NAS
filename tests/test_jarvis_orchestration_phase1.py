import pytest

from runtime.orchestration_policy import Capability, Decision, PolicyEngine
from runtime.orchestration_tools import ToolRegistry, ToolSpec
from runtime.orchestration_verifier import VerificationResult, verify_result


def test_policy_fails_closed_on_invalid_request():
    policy = PolicyEngine()
    decision = policy.evaluate(tool_name="status.health", capability="read_runtime", risk="low", payload={})
    assert decision.decision == Decision.ALLOW
    assert decision.reason

    denied = policy.evaluate(tool_name="shell.exec", capability="execute_safe", risk="low", payload={})
    assert denied.decision == Decision.DENY
    assert "capability" in denied.reason.lower()


def test_model_cannot_grant_itself_capability():
    policy = PolicyEngine()
    with pytest.raises(ValueError):
        policy.evaluate(tool_name="x", capability=Capability.SYSTEM_MUTATION, risk="low", payload={})


def test_registry_validates_schema_and_capability():
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="status.health",
            capability=Capability.READ_RUNTIME,
            risk="low",
            input_schema={"type": "object", "additionalProperties": False},
            handler=lambda payload: {"status": "healthy"},
        )
    )
    assert registry.get("status.health").capability == Capability.READ_RUNTIME
    with pytest.raises(ValueError):
        registry.register(registry.get("status.health"))


def test_verifier_fails_closed_on_missing_success_marker():
    result = verify_result("status.health", {"status": "unknown"})
    assert isinstance(result, VerificationResult)
    assert not result.ok


def test_verifier_accepts_known_health_result():
    result = verify_result("status.health", {"status": "healthy"})
    assert result.ok
