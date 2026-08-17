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


def test_unknown_tool_is_rejected():
    with pytest.raises(KeyError):
        ToolGateway().execute("status.missing", {})


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


def test_write_session_is_allowed_only_for_low_risk_session_tools():
    gateway = ToolGateway()
    gateway.register(ToolSpec("todo.create", Capability.WRITE_SESSION, RiskLevel.LOW, identity, identity))
    assert gateway.execute("todo.create", {"id": "x", "title": "ok"}) == {"id": "x", "title": "ok"}
    assert gateway.audit_log[-1]["allowed"] is True

    high_risk = ToolGateway()
    high_risk.register(ToolSpec("todo.update", Capability.WRITE_SESSION, RiskLevel.HIGH, identity, identity))
    with pytest.raises(PermissionError, match="high-risk"):
        high_risk.execute("todo.update", {"id": "x", "title": "blocked"})


def test_default_gateway_registers_todo_control_plane_tools():
    gateway = build_default_gateway(lambda commits: {"recent_commits": list(range(commits))})
    assert {"todo.create", "todo.update", "todo.list"}.issubset(gateway._tools)


def test_todo_create_validation_is_bounded_and_strict():
    gateway = build_default_gateway(lambda commits: {})
    valid = {"id": "T-1", "title": "Fix runtime", "description": "close policy gap", "status": "pending"}
    assert gateway.execute("todo.create", valid)["id"] == "T-1"
    for payload in (
        {"id": "", "title": "x"},
        {"id": "T-1", "title": ""},
        {"id": "T-1", "title": "x", "unexpected": True},
        {"id": "T-1", "title": "x", "status": "invalid"},
        {"id": "T-1", "title": "x", "description": "x" * 5001},
    ):
        with pytest.raises(ValueError):
            gateway.execute("todo.create", payload)


def test_todo_update_validation_requires_id_and_known_fields():
    gateway = build_default_gateway(lambda commits: {})
    assert gateway.execute("todo.update", {"id": "T-1", "status": "done"})["id"] == "T-1"
    with pytest.raises(ValueError):
        gateway.execute("todo.update", {"status": "done"})
    with pytest.raises(ValueError):
        gateway.execute("todo.update", {"id": "T-1", "created_at": "now"})
    with pytest.raises(ValueError):
        gateway.execute("todo.update", {"id": "", "status": "done"})


def test_todo_list_validation_is_strict():
    gateway = build_default_gateway(lambda commits: {})
    result = gateway.execute("todo.list", {})
    assert "todos" in result
    with pytest.raises(ValueError):
        gateway.execute("todo.list", {"unexpected": True})
    with pytest.raises(ValueError):
        gateway.execute("todo.list", {"limit": 0})
    with pytest.raises(ValueError):
        gateway.execute("todo.list", {"limit": 101})


def test_todo_mutations_are_audited():
    gateway = build_default_gateway(lambda commits: {})
    gateway.execute("todo.create", {"id": "AUDIT-1", "title": "Audit me"})
    assert gateway.audit_log[-1]["tool"] == "todo.create"
    assert gateway.audit_log[-1]["allowed"] is True


def test_default_gateway_registers_exact_control_plane_tools():
    gateway = build_default_gateway(lambda commits: {"recent_commits": list(range(commits))})
    assert set(gateway._tools) == {
        "status.health",
        "status.progress",
        "prompt.get",
        "memory.read",
        "todo.create",
        "todo.update",
        "todo.list",
    }
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
