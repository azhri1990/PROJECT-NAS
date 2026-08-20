"""Small persistent queue loop for constrained PROJECT-BOB autopilot."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .bob_autopilot import AutopilotAction, decide_next
from .bob_autopilot_runner import run_step


class AutopilotLoop:
    def __init__(self, *, queue_path: Path | str, events_path: Path | str, cwd: Path | str = ".") -> None:
        self.queue_path = Path(queue_path)
        self.events_path = Path(events_path)
        self.cwd = Path(cwd)
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self.events_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_queue(self) -> list[dict[str, Any]]:
        if not self.queue_path.exists():
            return []
        data = json.loads(self.queue_path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, list):
            raise ValueError("autopilot queue must be a JSON list")
        return data

    def _write_event(self, task_id: str, action: str, **extra: Any) -> None:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "action": action,
            **extra,
        }
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    def _write_queue(self, remaining: list[dict[str, Any]]) -> None:
        payload = json.dumps(remaining, indent=2) + "\n"
        temp = self.queue_path.with_name(f"{self.queue_path.name}.{os.getpid()}.tmp")
        temp.write_text(payload, encoding="utf-8")
        temp.replace(self.queue_path)

    def run_once(self) -> dict[str, int]:
        queue = self._load_queue()
        remaining: list[dict[str, Any]] = []
        completed = 0
        escalated = 0

        for task in queue:
            task_id = str(task.get("id", ""))
            step = str(task.get("step", ""))
            risk = str(task.get("risk", "routine"))
            max_retries = int(task.get("max_retries", 2))
            attempt = int(task.get("attempt", 0))
            if not task_id or not step:
                escalated += 1
                self._write_event(task_id or "unknown", "ESCALATE", reason="malformed task")
                continue

            result = run_step(step, cwd=self.cwd)
            if result.ok:
                decision = decide_next(
                    risk=risk,
                    verified=True,
                    attempt=attempt,
                    max_retries=max_retries,
                )
                if decision.action is AutopilotAction.PROCEED:
                    completed += 1
                    self._write_event(task_id, "COMPLETED", step=step, attempt=attempt)
                else:
                    escalated += 1
                    self._write_event(task_id, "ESCALATE", step=step, reason=decision.reason)
                continue

            decision = decide_next(
                risk=risk,
                verified=False,
                attempt=attempt,
                max_retries=max_retries,
                failure_class=f"step:{step}",
            )
            self._write_event(task_id, decision.action.value.upper(), step=step, attempt=decision.attempt, reason=result.error or "step failed")
            if decision.action is AutopilotAction.RETRY:
                updated = dict(task)
                updated["attempt"] = decision.attempt
                remaining.append(updated)
            else:
                escalated += 1

        self._write_queue(remaining)
        return {"completed": completed, "escalated": escalated}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    loop = AutopilotLoop(
        queue_path=root / "runtime" / "bob-autopilot-queue.json",
        events_path=root / "runtime" / "bob-autopilot-events.jsonl",
        cwd=root,
    )
    print(json.dumps(loop.run_once(), sort_keys=True))
