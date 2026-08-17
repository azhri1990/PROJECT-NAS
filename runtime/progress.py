#!/usr/bin/env python3
"""Report repository state and optionally read todos from a SQLite DB."""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.git_reader import get_repo_info


def read_todos_from_db(db_path):
    if not os.path.exists(db_path):
        return {"error": f"DB path does not exist: {db_path}"}
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT id, title, status, description, created_at, updated_at "
                "FROM todos ORDER BY created_at"
            ).fetchall()
        return {
            "todos": [
                {
                    "id": row[0],
                    "title": row[1],
                    "status": row[2],
                    "description": row[3],
                    "created_at": row[4],
                    "updated_at": row[5],
                }
                for row in rows
            ]
        }
    except sqlite3.Error as exc:
        return {"error": str(exc)}


def main():
    parser = argparse.ArgumentParser(description="PROJECT-NAS progress reporter")
    parser.add_argument("--session-db", "-d", help="SQLite session DB containing todos")
    parser.add_argument("--output", "-o", help="Write JSON output to file")
    parser.add_argument("--commits", "-n", type=int, default=10)
    args = parser.parse_args()

    if args.commits < 0:
        parser.error("--commits must be non-negative")

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "repo": get_repo_info(commits=args.commits),
    }
    if args.session_db:
        result["session"] = read_todos_from_db(args.session_db)

    text = json.dumps(result, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"Wrote progress JSON to {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
