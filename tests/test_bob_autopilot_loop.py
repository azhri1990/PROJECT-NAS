import json
from pathlib import Path

from runtime.bob_autopilot_loop import AutopilotLoop


def test_loop_executes_queue_and_records_results(tmp_path: Path, monkeypatch):
    queue = tmp_path / "queue.json"
    events = tmp_path / "events.jsonl"
    queue.write_text(
        json.dumps(
            [
                {"id": "t1", "step": "compile", "risk": "routine", "max_retries": 1},
            ]
        ),
        encoding="utf-8",
    )

    calls = []

    def fake_run_step(step, *, cwd):
        calls.append(step)
        return type("R", (), {"ok": True, "output": "ok", "error": "", "returncode": 0})()

    monkeypatch.setattr("runtime.bob_autopilot_loop.run_step", fake_run_step)
    loop = AutopilotLoop(queue_path=queue, events_path=events, cwd=tmp_path)
    results = loop.run_once()

    assert results == {"completed": 1, "escalated": 0}
    assert calls == ["compile"]
    assert "t1" in events.read_text(encoding="utf-8")


def test_loop_escalates_after_retry_budget(tmp_path: Path, monkeypatch):
    queue = tmp_path / "queue.json"
    events = tmp_path / "events.jsonl"
    queue.write_text(
        json.dumps(
            [
                {"id": "t2", "step": "pytest", "risk": "routine", "max_retries": 1},
            ]
        ),
        encoding="utf-8",
    )

    calls = []

    def fake_run_step(step, *, cwd):
        calls.append(step)
        return type("R", (), {"ok": False, "output": "", "error": "broken", "returncode": 1})()

    monkeypatch.setattr("runtime.bob_autopilot_loop.run_step", fake_run_step)
    loop = AutopilotLoop(queue_path=queue, events_path=events, cwd=tmp_path)
    results = loop.run_once()

    assert results == {"completed": 0, "escalated": 1}
    assert calls == ["pytest", "pytest"]
