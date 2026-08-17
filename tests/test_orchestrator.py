import pytest

from runtime.local_model_router import ModelRoute
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


def test_generate_response_composes_bounded_memory_and_user_context():
    calls = []

    class Gateway:
        def execute(self, name, payload):
            calls.append((name, payload))
            if name == "prompt.get":
                return {"content": "SYSTEM"}
            if name == "memory.read":
                return {"memories": [{"document": "MEMORY"}]}
            raise AssertionError(name)

    class Model:
        def generate_with_fallback(self, prompt, *, timeout, num_predict):
            assert "[SYSTEM]\nSYSTEM" in prompt
            assert "[MEMORY]\nMEMORY" in prompt
            assert "[USER]\nUSER REQUEST" in prompt
            assert len(prompt) <= 200
            return {"response": "ok"}, ModelRoute("llama3.2:3b", "llama3.2:3b", ("llama3.2:3b",), False)

    router = IntentRouter(Gateway(), Model())
    result, route, truncated = router.generate_response("USER REQUEST", max_chars=200)

    assert result == {"response": "ok"}
    assert route.selected == "llama3.2:3b"
    assert truncated is False
    assert calls == [
        ("prompt.get", {"max_chars": 200}),
        ("memory.read", {"query": None, "limit": 5}),
    ]


def test_generate_response_rejects_oversized_user_input():
    class Model:
        def generate_with_fallback(self, *args, **kwargs):
            raise AssertionError("model must not be called")

    router = IntentRouter(ToolGateway(), Model())
    with pytest.raises(ValueError, match="user_input exceeds maximum length"):
        router.generate_response("x" * 8001)
