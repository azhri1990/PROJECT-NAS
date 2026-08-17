from fastapi.testclient import TestClient

import runtime.backend as backend


def test_intent_endpoint_routes_allowlisted_intent(monkeypatch):
    calls = []

    class Router:
        def handle(self, intent, payload):
            calls.append((intent, payload))
            return {"ok": True, "intent": intent}

    monkeypatch.setattr(backend, "INTENT_ROUTER", Router())
    response = TestClient(backend.app).post("/intent/health", json={})

    assert response.status_code == 200
    assert response.json() == {"ok": True, "intent": "health"}
    assert calls == [("health", {})]


def test_intent_endpoint_rejects_unknown_intent(monkeypatch):
    class Router:
        def handle(self, intent, payload):
            raise PermissionError("intent denied")

    monkeypatch.setattr(backend, "INTENT_ROUTER", Router())
    response = TestClient(backend.app).post("/intent/shell", json={"command": "id"})

    assert response.status_code == 403
    assert response.json()["detail"] == "intent denied"


def test_intent_endpoint_does_not_expose_arbitrary_tool_selection(monkeypatch):
    calls = []

    class Router:
        def handle(self, intent, payload):
            calls.append((intent, payload))
            raise PermissionError("intent denied")

    monkeypatch.setattr(backend, "INTENT_ROUTER", Router())
    response = TestClient(backend.app).post("/intent/status.health", json={})

    assert response.status_code == 403
    assert calls == [("status.health", {})]


def test_intent_endpoint_maps_validation_errors(monkeypatch):
    class Router:
        def handle(self, intent, payload):
            raise ValueError("unsupported arguments")

    monkeypatch.setattr(backend, "INTENT_ROUTER", Router())
    response = TestClient(backend.app).post("/intent/progress", json={"bad": True})

    assert response.status_code == 400
    assert response.json()["detail"] == "unsupported arguments"


def test_intent_endpoint_bounds_intent_name():
    response = TestClient(backend.app).post("/intent/" + "x" * (backend.MAX_INTENT_CHARS + 1), json={})

    assert response.status_code == 413


def test_intent_endpoint_maps_gateway_timeout(monkeypatch):
    class Router:
        def handle(self, intent, payload):
            raise TimeoutError("tool timed out")

    monkeypatch.setattr(backend, "INTENT_ROUTER", Router())
    response = TestClient(backend.app).post("/intent/health", json={})

    assert response.status_code == 504
    assert response.json()["detail"] == "tool timed out"
