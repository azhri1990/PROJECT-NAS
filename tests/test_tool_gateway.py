import time

import pytest

from runtime.policy import Capability, PolicyEngine, RiskLevel
from runtime.tool_gateway import ToolGateway, ToolSpec, build_default_gateway


def test_registered_read_tool_executes_after_policy_check():
    gateway = ToolGateway()
    calls = []
    gateway.register(ToolSpec(
        name="status.health",
        capability=Capability.READ_RUNTIME,
        risk=RiskLevel.LOW,
        input_validator=lambda payload: payload,
        handler=lambda payload: calls.append(payload) or {"ok": True},
    ))

    result = gateway.execute("status.health", {})

    assert result == {"ok": True}
    assert calls == [{}]
    assert gateway.audit_log[-1]["allowed"] is True


def test_unknown_tool_is_rejected_and_audited():
    gateway = ToolGateway()
    with pytest.raises(KeyError):
        gateway.execute("status.missing", {})
    assert gateway.audit_log[-1] == {
        "tool": "status.missing",
        "allowed": False,
        "reason": "unknown tool denied",
    }


def test_denied_capability_never_calls_handler():
    gateway = ToolGateway()
    calls = []
    gateway.register(ToolSpec(
        name="status.danger",
        capability=Capability.EXECUTE_PROCESS,
        risk=RiskLevel.HIGH,
        input_validator=lambda payload: payload,
        handler=lambda payload: calls.append(payload),
    ))

    with pytest.raises(PermissionError):
        gateway.execute("status.danger", {})

    assert calls == []
    assert gateway.audit_log[-1]["allowed"] is False


def test_invalid_payload_is_rejected_before_handler():
    gateway = ToolGateway()
    calls = []
    gateway.register(ToolSpec(
        name="status.strict",
        capability=Capability.READ_RUNTIME,
        risk=RiskLevel.LOW,
        input_validator=lambda payload: (_ for _ in ()).throw(ValueError("bad payload")),
        handler=lambda payload: calls.append(payload),
    ))

    with pytest.raises(ValueError, match="bad payload"):
        gateway.execute("status.strict", {})

    assert calls == []
    assert gateway.audit_log == []


def test_timeout_raises_without_returning_handler_result():
    gateway = ToolGateway()
    gateway.register(ToolSpec(
        name="status.slow",
        capability=Capability.READ_RUNTIME,
        risk=RiskLevel.LOW,
        input_validator=lambda payload: payload,
        handler=lambda payload: time.sleep(0.2),
        timeout_seconds=0.01,
    ))

    with pytest.raises(TimeoutError, match="status.slow"):
        gateway.execute("status.slow", {})


def test_write_repository_is_denied_by_default():
    gateway = ToolGateway()
    gateway.register(ToolSpec(
        name="status.write",
        capability=Capability.WRITE_REPOSITORY,
        risk=RiskLevel.LOW,
        input_validator=lambda payload: payload,
        handler=lambda payload: {"should": "never run"},
    ))

    with pytest.raises(PermissionError, match="write_repository"):
        gateway.execute("status.write", {})


def test_default_gateway_registers_only_allowlisted_status_tools():
    gateway = build_default_gateway(progress_handler=lambda commits: {"commits": commits})
    assert set(gateway._tools) == {"status.health", "status.progress", "prompt.get", "memory.read"}
