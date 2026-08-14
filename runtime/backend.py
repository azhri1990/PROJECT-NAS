from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import sqlite3
import os
import subprocess
import json
import importlib.util
from typing import Any, Dict

app = FastAPI(title="PROJECT-NAS Local Backend")

SESSION_DB = os.path.expanduser(os.path.join('C:', 'Users', 'nashr', '.copilot', 'session-state', 'aaff7648-a36a-4708-b660-48d0f44fcfc3', 'files', 'session.db'))
# Fallback to local file in repo
if not os.path.exists(SESSION_DB):
    SESSION_DB = os.path.join(os.path.dirname(__file__), '..', 'session.db')

PROMPT_PATHS = [
    os.path.join(os.path.dirname(__file__), '..', 'ai', 'MASTER_PROMPT.md'),
    os.path.join(os.path.dirname(__file__), '..', 'ai', 'AI_OPERATING_SYSTEM_SUMMARY.md'),
]

PLUGIN_DIR = os.path.join(os.path.dirname(__file__), 'plugins')
if not os.path.exists(PLUGIN_DIR):
    os.makedirs(PLUGIN_DIR, exist_ok=True)


def load_prompt() -> Dict[str, Any]:
    for p in PROMPT_PATHS:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return { 'path': p, 'prompt': f.read() }
    return { 'path': None, 'prompt': '' }


def run_git_info(commits: int = 10) -> Dict[str, Any]:
    try:
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).strip()
    except Exception:
        branch = None
    try:
        status = subprocess.check_output(['git', 'status', '--porcelain', '--branch'], text=True)
    except Exception:
        status = ''
    try:
        log = subprocess.check_output(['git', 'log', '--oneline', '-n', str(commits)], text=True)
        recent = [l.strip() for l in log.splitlines() if l.strip()]
    except Exception:
        recent = []
    return {'branch': branch, 'status_porcelain': status, 'recent_commits': recent}


def get_db_conn():
    if not os.path.exists(SESSION_DB):
        # create minimal session db with todos if missing
        conn = sqlite3.connect(SESSION_DB)
        conn.execute('''CREATE TABLE IF NOT EXISTS todos (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )''')
        conn.commit()
        return conn
    return sqlite3.connect(SESSION_DB)


@app.get('/prompt')
async def get_prompt():
    return load_prompt()


@app.get('/progress')
async def progress(commits: int = 10):
    return run_git_info(commits)


@app.get('/todos')
async def list_todos():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, title, description, status, created_at, updated_at FROM todos ORDER BY created_at")
    rows = cur.fetchall()
    conn.close()
    todos = []
    for r in rows:
        todos.append({
            'id': r[0], 'title': r[1], 'description': r[2], 'status': r[3], 'created_at': r[4], 'updated_at': r[5]
        })
    return {'todos': todos}


@app.post('/todos')
async def create_todo(item: Dict[str, Any]):
    if 'id' not in item or 'title' not in item:
        raise HTTPException(status_code=400, detail='id and title required')
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO todos (id, title, description, status) VALUES (?, ?, ?, ?)',
                    (item['id'], item['title'], item.get('description'), item.get('status', 'pending')))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail='todo with id already exists')
    finally:
        conn.close()
    return {'created': True, 'id': item['id']}


@app.put('/todos/{todo_id}')
async def update_todo(todo_id: str, item: Dict[str, Any]):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM todos WHERE id=?', (todo_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail='todo not found')
    updates = []
    params = []
    for k in ('title','description','status'):
        if k in item:
            updates.append(f"{k} = ?")
            params.append(item[k])
    if updates:
        params.append(todo_id)
        cur.execute(f"UPDATE todos SET {', '.join(updates)}, updated_at = datetime('now') WHERE id = ?", params)
        conn.commit()
    conn.close()
    return {'updated': True, 'id': todo_id}


@app.post('/custom/{plugin_name}')
async def run_custom(plugin_name: str, payload: Dict[str, Any]):
    # Security note: this executes local plugin code. Only use trusted plugins.
    plugin_path = os.path.join(PLUGIN_DIR, f"{plugin_name}.py")
    if not os.path.exists(plugin_path):
        raise HTTPException(status_code=404, detail='plugin not found')
    spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, 'handle'):
        raise HTTPException(status_code=400, detail='plugin must implement handle(payload)')
    try:
        result = module.handle(payload)
        return JSONResponse(content={'result': result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/')
async def root():
    return {'service': 'PROJECT-NAS local backend', 'version': '0.1'}
