import pytest

from runtime.orchestrator import IntentRouter
from runtime.tool_gateway import ToolGateway


def test_routes_only_fixed_read_intents():
    calls = []

    class Gateway:
        def execute(self, name, payload):
            calls.append((name, payload))
            return {"ok": True}

    router = IntentRouter(Gateway())
    assert router.handle("health") == {"ok": True}
    assert router.handle("progress", {"commits": 2}) == {"ok": True}
    assert router.handle("memory", {"query": "runtime", "limit": 2}) == {"ok": True}
    assert router.handle("prompt", {"max_chars": 100}) == {"ok": True}
    assert calls == [
        ("status.health", {}),
        ("status.progress", {"commits": 2}),
        ("memory.read", {"query": "runtime", "limit": 2}),
        ("prompt.get", {"max_chars": 100}),
    ]


def test_unknown_intent_is_denied():
    router = IntentRouter(ToolGateway())
    with pytest.raises(PermissionError, match="intent denied"):
        router.handle("shell")


def test_intent_cannot_be_used_to_select_arbitrary_tool():
    calls = []

    class Gateway:
        def execute(self, name, payload):
            calls.append(name)
            return {}

    router = IntentRouter(Gateway())
    with pytest.raises(PermissionError):
        router.handle("shell.run")
    assert calls == []


def test_payload_must_be_object():
    router = IntentRouter(ToolGateway())
    with pytest.raises(ValueError, match="payload must be an object"):
        router.handle("health", [])


def test_gateway_errors_are_not_swallowed():
    class Gateway:
        def execute(self, name, payload):
            raise PermissionError("blocked")

    router = IntentRouter(Gateway())
    with pytest.raises(PermissionError, match="blocked"):
        router.handle("health")
