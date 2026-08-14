#!/usr/bin/env python3
"""
Simple progress reporter for this repository.
Outputs JSON with git branch, recent commits, working-tree status, and (optionally) todos from a provided SQLite session DB.

Usage:
  python runtime/progress.py [--session-db PATH] [--output FILE] [--commits N]

If --session-db is provided and points to a SQLite DB containing a 'todos' table matching the session schema, those todos will be included.
"""

import argparse
import json
import os
import subprocess
import sys
import sqlite3
from datetime import datetime


def run_git(cmd_args):
    try:
        out = subprocess.check_output(['git'] + cmd_args, stderr=subprocess.DEVNULL, text=True)
        return out.strip()
    except Exception:
        return None


def get_repo_info(commits=10):
    info = {}
    branch = run_git(['rev-parse', '--abbrev-ref', 'HEAD'])
    info['branch'] = branch or 'unknown'

    status = run_git(['status', '--porcelain', '--branch'])
    info['status_porcelain'] = status or ''

    log = run_git(['log', '--oneline', '-n', str(commits)])
    info['recent_commits'] = log.splitlines() if log else []
    return info


def read_todos_from_db(db_path):
    if not os.path.exists(db_path):
        return {'error': f"DB path does not exist: {db_path}"}
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, title, status, description, created_at, updated_at FROM todos ORDER BY created_at")
        rows = cur.fetchall()
        todos = []
        for r in rows:
            todos.append({
                'id': r[0],
                'title': r[1],
                'status': r[2],
                'description': r[3],
                'created_at': r[4],
                'updated_at': r[5],
            })
        conn.close()
        return {'todos': todos}
    except Exception as e:
        return {'error': str(e)}


def main():
    p = argparse.ArgumentParser(description='Progress reporter')
    p.add_argument('--session-db', '-d', help='Path to SQLite session DB containing todos table')
    p.add_argument('--output', '-o', help='Write JSON output to file')
    p.add_argument('--commits', '-n', type=int, default=10, help='Number of recent commits to include')
    args = p.parse_args()

    result = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'repo': get_repo_info(commits=args.commits)
    }

    if args.session_db:
        result['session'] = read_todos_from_db(args.session_db)

    text = json.dumps(result, indent=2)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f'Wrote progress JSON to {args.output}')
    else:
        print(text)

if __name__ == '__main__':
    main()
