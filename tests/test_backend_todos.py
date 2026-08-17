import asyncio

import pytest

from runtime import backend


class GatewaySpy:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    def execute(self, name, payload):
        self.calls.append((name, payload))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_create_todo_endpoint_uses_gateway_instead_of_direct_sql(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_NAS_SESSION_DB", str(tmp_path / "session.db"))
    spy = GatewaySpy({"created": True, "id": "T-1"})
    monkeypatch.setattr(backend, "TOOL_GATEWAY", spy)

    result = asyncio.run(backend.create_todo({"id": "T-1", "title": "Secure path"}))

    assert result == {"created": True, "id": "T-1"}
    assert spy.calls == [("todo.create", {"id": "T-1", "title": "Secure path"})]
    assert not (tmp_path / "session.db").exists()


def test_update_todo_endpoint_uses_gateway_and_overrides_body_id(monkeypatch):
    spy = GatewaySpy({"updated": True, "id": "T-9"})
    monkeypatch.setattr(backend, "TOOL_GATEWAY", spy)

    result = asyncio.run(backend.update_todo("T-9", {"title": "Updated", "id": "attacker-value"}))

    assert result == {"updated": True, "id": "T-9"}
    assert spy.calls == [("todo.update", {"title": "Updated", "id": "T-9"})]


def test_list_todo_endpoint_uses_bounded_gateway_read(monkeypatch):
    spy = GatewaySpy({"todos": []})
    monkeypatch.setattr(backend, "TOOL_GATEWAY", spy)

    result = asyncio.run(backend.list_todos(7))

    assert result == {"todos": []}
    assert spy.calls == [("todo.list", {"limit": 7})]


def test_todo_gateway_persists_and_rejects_duplicates(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_NAS_SESSION_DB", str(tmp_path / "session.db"))

    assert backend.TOOL_GATEWAY.execute(
        "todo.create",
        {"id": "T-1", "title": "First", "description": None, "status": "pending"},
    ) == {"created": True, "id": "T-1"}

    with pytest.raises(backend.TodoConflictError, match="already exists"):
        backend.TOOL_GATEWAY.execute(
            "todo.create",
            {"id": "T-1", "title": "Duplicate", "description": None, "status": "pending"},
        )

    result = backend.TOOL_GATEWAY.execute("todo.list", {"limit": 10})
    assert [todo["id"] for todo in result["todos"]] == ["T-1"]


def test_todo_gateway_update_requires_existing_id(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_NAS_SESSION_DB", str(tmp_path / "session.db"))

    with pytest.raises(backend.TodoNotFoundError, match="todo not found"):
        backend.TOOL_GATEWAY.execute("todo.update", {"id": "missing", "status": "done"})


def test_todo_http_errors_preserve_existing_contract(monkeypatch):
    monkeypatch.setattr(backend, "TOOL_GATEWAY", GatewaySpy(backend.TodoConflictError("todo with id already exists")))
    with pytest.raises(backend.HTTPException) as conflict:
        asyncio.run(backend.create_todo({"id": "T-1", "title": "Duplicate"}))
    assert conflict.value.status_code == 409

    monkeypatch.setattr(backend, "TOOL_GATEWAY", GatewaySpy(backend.TodoNotFoundError("todo not found")))
    with pytest.raises(backend.HTTPException) as missing:
        asyncio.run(backend.update_todo("missing", {"status": "done"}))
    assert missing.value.status_code == 404
