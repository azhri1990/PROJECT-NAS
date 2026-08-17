import json

from fastapi.testclient import TestClient

import runtime.backend as backend


def test_chat_rejects_missing_prompt():
    response = TestClient(backend.app).post("/chat", json={})
    assert response.status_code == 400


def test_chat_rejects_oversized_prompt():
    response = TestClient(backend.app).post("/chat", json={"prompt": "x" * (backend.MAX_CHAT_PROMPT_CHARS + 1)})
    assert response.status_code == 413


def test_chat_rejects_remote_worker(monkeypatch):
    monkeypatch.setenv("PROJECT_NAS_CHAT_WORKER_URL", "https://example.com/chat")
    response = TestClient(backend.app).post("/chat", json={"prompt": "hello"})
    assert response.status_code == 503


def test_chat_forwards_prompt_and_context_and_allowlists_response(monkeypatch):
    captured = {}

    class FakeResponse:
        status = 200

        def read(self, limit):
            captured["read_limit"] = limit
            return json.dumps({
                "response": "hello back",
                "model": "llama3.2:3b",
                "secret": "do-not-forward",
            }).encode()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode())
        return FakeResponse()

    monkeypatch.setattr(backend, "urlopen", fake_urlopen)
    response = TestClient(backend.app).post(
        "/chat", json={"prompt": "hello", "context": "context"}
    )
    assert response.status_code == 200
    assert response.json() == {"response": "hello back", "model": "llama3.2:3b"}
    assert captured["url"] == "http://127.0.0.1:5000/chat"
    assert captured["body"] == {"context": "context", "prompt": "hello"}


def test_chat_rejects_invalid_worker_response(monkeypatch):
    class FakeResponse:
        status = 200

        def read(self, limit):
            return b'{"unexpected":"field"}'

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(backend, "urlopen", lambda *args, **kwargs: FakeResponse())
    response = TestClient(backend.app).post("/chat", json={"prompt": "hello"})
    assert response.status_code == 502


def test_chat_rejects_unsupported_fields():
    response = TestClient(backend.app).post(
        "/chat", json={"prompt": "hello", "network": True}
    )
    assert response.status_code == 400
