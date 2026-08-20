"""Persistent constrained PROJECT-BOB autopilot daemon."""
from __future__ import annotations

import json
import os
import signal
import time
from pathlib import Path

from .bob_autopilot_loop import AutopilotLoop


class SingleInstance:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._held = False

    def acquire(self) -> bool:
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        self._held = True
        return True

    def release(self) -> None:
        if self._held:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            self._held = False


class AutopilotDaemon:
    def __init__(self, root: Path, interval_seconds: float = 30.0) -> None:
        if interval_seconds < 1.0:
            raise ValueError("interval_seconds must be at least 1 second")
        self.root = root
        self.interval_seconds = interval_seconds
        self.running = True
        self.instance = SingleInstance(root / "runtime" / "bob-autopilot.pidlock")
        self.loop = AutopilotLoop(
            queue_path=root / "runtime" / "bob-autopilot-queue.json",
            events_path=root / "runtime" / "bob-autopilot-events.jsonl",
            cwd=root,
        )

    def stop(self, *_: object) -> None:
        self.running = False

    def run(self) -> int:
        if not self.instance.acquire():
            raise RuntimeError("BOB autopilot is already running")
        try:
            while self.running:
                summary = self.loop.run_once()
                status = {
                    "pid": os.getpid(),
                    "timestamp": time.time(),
                    "summary": summary,
                }
                (self.root / "runtime" / "bob-autopilot-status.json").write_text(
                    json.dumps(status, sort_keys=True) + "\n", encoding="utf-8"
                )
                if summary["completed"] == 0 and summary["escalated"] == 0:
                    time.sleep(self.interval_seconds)
                else:
                    time.sleep(min(self.interval_seconds, 5.0))
            return 0
        finally:
            self.instance.release()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    daemon = AutopilotDaemon(
        root,
        interval_seconds=float(os.environ.get("PROJECT_BOB_AUTOPILOT_INTERVAL", "30")),
    )
    signal.signal(signal.SIGINT, daemon.stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, daemon.stop)
    return daemon.run()


if __name__ == "__main__":
    raise SystemExit(main())
