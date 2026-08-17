import time

import pytest

from runtime.policy import Capability, RiskLevel
from runtime.tool_gateway import ToolGateway, ToolSpec, build_default_gateway


def identity(payload):
    return payload


def test_registered_read_tool_executes_after_policy_check():
    gateway = ToolGateway()
    gateway.register(
        ToolSpec(
            name="status.progress",
            capability=Capability.READ_REPOSITORY,
            risk=RiskLevel.LOW,
            input_validator=identity,
            handler=identity,
        )
    )
    assert gateway.execute("status.progress", {"commits": 3}) == {"commits": 3}
    assert gateway.audit_log[-1]["allowed"] is True


def test_unknown_tool_is_rejected():
    with pytest.raises(KeyError):
        ToolGateway().execute("status.missing", {})


def test_denied_capability_never_calls_handler():
    called = []
    gateway = ToolGateway()
    gateway.register(
        ToolSpec(
            name="shell.run",
            capability=Capability.EXECUTE_PROCESS,
            risk=RiskLevel.CRITICAL,
            input_validator=identity,
            handler=lambda payload: called.append(payload),
        )
    )
    with pytest.raises(PermissionError):
        gateway.execute("shell.run", {"command": "whoami"})
    assert called == []
    assert gateway.audit_log[-1]["allowed"] is False


def test_invalid_payload_is_rejected_before_handler():
    gateway = ToolGateway()
    gateway.register(
        ToolSpec(
            name="memory.validated",
            capability=Capability.READ_RUNTIME,
            risk=RiskLevel.LOW,
            input_validator=lambda payload: (_ for _ in ()).throw(ValueError("bad payload")),
            handler=identity,
        )
    )
    with pytest.raises(ValueError, match="bad payload"):
        gateway.execute("memory.validated", {})


def test_timeout_raises_without_returning_handler_result():
    gateway = ToolGateway()

    def slow_handler(payload):
        time.sleep(0.2)
        return payload

    gateway.register(
        ToolSpec(
            name="status.slow",
            capability=Capability.READ_RUNTIME,
            risk=RiskLevel.LOW,
            input_validator=identity,
            handler=slow_handler,
            timeout_seconds=0.01,
        )
    )
    with pytest.raises(TimeoutError, match="tool timed out: status.slow"):
        gateway.execute("status.slow", {})

def test_write_repository_is_denied_by_default():
    gateway = ToolGateway()
    gateway.register(
        ToolSpec(
            name="status.todo.create",
            capability=Capability.WRITE_REPOSITORY,
            risk=RiskLevel.MEDIUM,
            input_validator=identity,
            handler=lambda payload: payload,
        )
    )

    with pytest.raises(PermissionError, match="write_repository"):
        gateway.execute("status.todo.create", {"id": "x", "title": "blocked"})

    assert gateway.audit_log[-1]["allowed"] is False


def test_default_gateway_registers_only_allowlisted_status_tools():
    gateway = build_default_gateway(lambda commits: {
        "recent_commits": list(range(commits))
    })

    assert gateway.execute("status.progress", {"commits": 2}) == {
        "recent_commits": [0, 1]
    }

    with pytest.raises(PermissionError):
        gateway.execute("repo.progress", {"commits": 2})

@pytest.mark.parametrize("name", ["shell.run", "process.run", "plugin.load", "custom.test", "network.call", "repo.progress", "unknown.tool"])
def test_non_allowlisted_namespaces_are_denied_before_handler(name):
    called=[]
    gateway=ToolGateway()
    gateway.register(ToolSpec(name=name, capability=Capability.READ_RUNTIME, risk=RiskLevel.LOW, input_validator=lambda payload: called.append("validator") or payload, handler=lambda payload: called.append("handler") or payload))
    with pytest.raises(PermissionError):
        gateway.execute(name, {})
    assert called == []
    assert gateway.audit_log[-1]["allowed"] is False

@pytest.mark.parametrize("name", ["memory.read", "prompt.get", "status.health"])
def test_allowlisted_namespaces_are_permitted(name):
    gateway=ToolGateway()
    gateway.register(ToolSpec(name=name, capability=Capability.READ_RUNTIME, risk=RiskLevel.LOW, input_validator=identity, handler=identity))
    assert gateway.execute(name, {"ok": True}) == {"ok": True}
    assert gateway.audit_log[-1]["allowed"] is True
