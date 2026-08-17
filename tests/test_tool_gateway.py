import time

import pytest

from runtime.policy import Capability, RiskLevel
from runtime.tool_gateway import ToolGateway, ToolSpec, build_default_gateway


def identity(payload):
    return payload


def test_registered_read_tool_executes_after_policy_check():
    gateway = ToolGateway()
    gateway.register(ToolSpec("status.progress", Capability.READ_REPOSITORY, RiskLevel.LOW, identity, identity))
    assert gateway.execute("status.progress", {"commits": 3}) == {"commits": 3}
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
    called = []
    gateway = ToolGateway()
    gateway.register(ToolSpec("shell.run", Capability.EXECUTE_PROCESS, RiskLevel.CRITICAL, identity, lambda payload: called.append(payload)))
    with pytest.raises(PermissionError):
        gateway.execute("shell.run", {"command": "whoami"})
    assert called == []
    assert gateway.audit_log[-1]["allowed"] is False


def test_invalid_payload_is_rejected_before_handler():
    gateway = ToolGateway()
    gateway.register(ToolSpec("memory.validated", Capability.READ_RUNTIME, RiskLevel.LOW, lambda payload: (_ for _ in ()).throw(ValueError("bad payload")), identity))
    with pytest.raises(ValueError, match="bad payload"):
        gateway.execute("memory.validated", {})


def test_timeout_raises_without_returning_handler_result():
    gateway = ToolGateway()
    def slow_handler(payload):
        time.sleep(0.2)
        return payload
    gateway.register(ToolSpec("status.slow", Capability.READ_RUNTIME, RiskLevel.LOW, identity, slow_handler, timeout_seconds=0.01))
    with pytest.raises(TimeoutError, match="tool timed out: status.slow"):
        gateway.execute("status.slow", {})


def test_write_repository_is_denied_by_default():
    gateway = ToolGateway()
    gateway.register(ToolSpec("status.todo.create", Capability.WRITE_REPOSITORY, RiskLevel.MEDIUM, identity, identity))
    with pytest.raises(PermissionError, match="write_repository"):
        gateway.execute("status.todo.create", {"id": "x", "title": "blocked"})
    assert gateway.audit_log[-1]["allowed"] is False


def test_default_gateway_registers_exact_control_plane_tools():
    gateway = build_default_gateway(lambda commits: {"recent_commits": list(range(commits))})
    assert set(gateway._tools) == {"status.health", "status.progress", "prompt.get", "memory.read"}
    assert gateway.execute("status.progress", {"commits": 2}) == {"recent_commits": [0, 1]}


def test_progress_boolean_and_bounds_are_rejected():
    gateway = build_default_gateway(lambda commits: {})
    for value in (True, 0, 51):
        with pytest.raises(ValueError, match="commits"):
            gateway.execute("status.progress", {"commits": value})


def test_memory_limit_defaults_and_bounds():
    gateway = build_default_gateway(lambda commits: {})
    result = gateway.execute("memory.read", {})
    assert result["count"] >= 0
    with pytest.raises(ValueError, match="limit"):
        gateway.execute("memory.read", {"limit": 51})
    with pytest.raises(ValueError, match="limit"):
        gateway.execute("memory.read", {"limit": 0})
    with pytest.raises(ValueError, match="limit"):
        gateway.execute("memory.read", {"limit": True})


def test_memory_query_validation():
    gateway = build_default_gateway(lambda commits: {})
    with pytest.raises(ValueError, match="query"):
        gateway.execute("memory.read", {"query": 123})
    with pytest.raises(ValueError, match="query"):
        gateway.execute("memory.read", {"query": "x" * 501})
    with pytest.raises(ValueError, match="unsupported"):
        gateway.execute("memory.read", {"unknown": True})


def test_prompt_validation_and_bounds():
    gateway = build_default_gateway(lambda commits: {})
    result = gateway.execute("prompt.get", {})
    assert set(result) == {"path", "content", "chars", "truncated"}
    assert result["chars"] == len(result["content"])
    with pytest.raises(ValueError, match="max_chars"):
        gateway.execute("prompt.get", {"max_chars": True})
    with pytest.raises(ValueError, match="max_chars"):
        gateway.execute("prompt.get", {"max_chars": 12001})
    with pytest.raises(ValueError, match="unsupported"):
        gateway.execute("prompt.get", {"content": 1})


@pytest.mark.parametrize("name", ["shell.run", "process.run", "plugin.load", "custom.test", "network.call", "repo.progress", "unknown.tool"])
def test_non_allowlisted_namespaces_are_denied_before_handler(name):
    called = []
    gateway = ToolGateway()
    gateway.register(ToolSpec(name, Capability.READ_RUNTIME, RiskLevel.LOW, lambda payload: called.append("validator") or payload, lambda payload: called.append("handler") or payload))
    with pytest.raises(PermissionError):
        gateway.execute(name, {})
    assert called == []
    assert gateway.audit_log[-1]["allowed"] is False


@pytest.mark.parametrize("name", ["memory.read", "prompt.get", "status.health"])
def test_allowlisted_namespaces_are_permitted(name):
    gateway = ToolGateway()
    gateway.register(ToolSpec(name, Capability.READ_RUNTIME, RiskLevel.LOW, identity, identity))
    assert gateway.execute(name, {"ok": True}) == {"ok": True}
    assert gateway.audit_log[-1]["allowed"] is True
