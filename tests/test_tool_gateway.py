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
            name="repo.progress",
            capability=Capability.READ_REPOSITORY,
            risk=RiskLevel.LOW,
            input_validator=identity,
            handler=identity,
        )
    )
    assert gateway.execute("repo.progress", {"commits": 3}) == {"commits": 3}
    assert gateway.audit_log[-1]["allowed"] is True


def test_unknown_tool_is_rejected():
    with pytest.raises(KeyError):
        ToolGateway().execute("missing", {})


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
            name="validated",
            capability=Capability.READ_RUNTIME,
            risk=RiskLevel.LOW,
            input_validator=lambda payload: (_ for _ in ()).throw(ValueError("bad payload")),
            handler=identity,
        )
    )
    with pytest.raises(ValueError, match="bad payload"):
        gateway.execute("validated", {})


def test_timeout_raises_without_returning_handler_result():
    gateway = ToolGateway()

    def slow_handler(payload):
        time.sleep(0.2)
        return payload

    gateway.register(
        ToolSpec(
            name="slow",
            capability=Capability.READ_RUNTIME,
            risk=RiskLevel.LOW,
            input_validator=identity,
            handler=slow_handler,
            timeout_seconds=0.01,
        )
    )
    with pytest.raises(TimeoutError, match="tool timed out: slow"):
        gateway.execute("slow", {})


def test_default_gateway_exposes_only_bounded_repository_progress():
    gateway = build_default_gateway(lambda commits: {"recent_commits": list(range(commits))})
    result = gateway.execute("repo.progress", {"commits": 2})
    assert result == {"recent_commits": [0, 1]}


def test_progress_validator_rejects_arbitrary_git_arguments():
    gateway = build_default_gateway(lambda commits: {"recent_commits": list(range(commits))})
    for payload in ({"command": "git reset --hard"}, {"commits": 0}, {"commits": 51}):
        with pytest.raises(ValueError):
            gateway.execute("repo.progress", payload)
