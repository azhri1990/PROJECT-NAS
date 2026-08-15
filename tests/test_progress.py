import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "runtime" / "progress.py"


def test_progress_reporter_json_shape():
    result = subprocess.run(
        [sys.executable, str(PROGRESS), "--commits", "3"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    repo = payload["repo"]

    assert payload["generated_at"]
    assert repo["branch"] not in (None, "", "unknown")
    assert isinstance(repo["status_porcelain"], str)
    assert isinstance(repo["recent_commits"], list)
    assert repo["recent_commits"]
    assert len(repo["recent_commits"]) <= 3


def test_progress_reporter_session_db(tmp_path):
    import sqlite3

    db = tmp_path / "session.db"
    conn = sqlite3.connect(db)
    conn.execute(
        """
        CREATE TABLE todos (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "INSERT INTO todos (id, title, status, description) VALUES (?, ?, ?, ?)",
        ("t1", "ci-test", "done", "validate progress reporter"),
    )
    conn.commit()
    conn.close()

    result = subprocess.run(
        [sys.executable, str(PROGRESS), "--session-db", str(db)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["session"]["todos"][0]["id"] == "t1"
    assert payload["session"]["todos"][0]["status"] == "done"
