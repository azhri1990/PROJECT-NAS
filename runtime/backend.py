from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import importlib.util
import os
import sqlite3
import subprocess
from typing import Any, Dict

from runtime.tool_gateway import build_default_gateway

app = FastAPI(title="PROJECT-NAS Local Backend")


def resolve_session_db() -> str:
    """Return the configured session database path, with a repo-local fallback."""
    configured = os.environ.get("PROJECT_NAS_SESSION_DB")
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "session.db"))


SESSION_DB = resolve_session_db()

PROMPT_PATHS = [
    os.path.join(os.path.dirname(__file__), "..", "ai", "MASTER_PROMPT.md"),
    os.path.join(os.path.dirname(__file__), "..", "ai", "AI_OPERATING_SYSTEM_SUMMARY.md"),
]

PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "plugins")
os.makedirs(PLUGIN_DIR, exist_ok=True)


def load_prompt() -> Dict[str, Any]:
    for path in PROMPT_PATHS:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                return {"path": path, "prompt": handle.read()}
    return {"path": None, "prompt": ""}


def run_git_info(commits: int = 10) -> Dict[str, Any]:
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
    except Exception:
        branch = None
    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain", "--branch"], text=True
        )
    except Exception:
        status = ""
    try:
        log = subprocess.check_output(
            ["git", "log", "--oneline", "-n", str(commits)], text=True
        )
        recent = [line.strip() for line in log.splitlines() if line.strip()]
    except Exception:
        recent = []
    return {"branch": branch, "status_porcelain": status, "recent_commits": recent}


TOOL_GATEWAY = build_default_gateway(run_git_info)


def get_db_conn():
    db_path = resolve_session_db()
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS todos (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )"""
    )
    conn.commit()
    return conn


def validate_plugin_name(plugin_name: str) -> str:
    """Allow only Python identifier-style plugin module names."""
    if not plugin_name or not plugin_name.isidentifier():
        raise ValueError("invalid plugin name")
    return plugin_name


@app.get("/prompt")
async def get_prompt():
    return load_prompt()


@app.get("/progress")
async def progress(commits: int = 10):
    return run_git_info(commits)


@app.post("/tools/{tool_name}")
async def execute_tool(tool_name: str, payload: Dict[str, Any]):
    try:
        return TOOL_GATEWAY.execute(tool_name, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="tool not found")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc


@app.get("/todos")
async def list_todos():
    conn = get_db_conn()
    try:
        rows = conn.execute(
            "SELECT id, title, description, status, created_at, updated_at "
            "FROM todos ORDER BY created_at"
        ).fetchall()
    finally:
        conn.close()
    return {
        "todos": [
            {
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "status": row[3],
                "created_at": row[4],
                "updated_at": row[5],
            }
            for row in rows
        ]
    }


@app.post("/todos")
async def create_todo(item: Dict[str, Any]):
    if "id" not in item or "title" not in item:
        raise HTTPException(status_code=400, detail="id and title required")
    conn = get_db_conn()
    try:
        conn.execute(
            "INSERT INTO todos (id, title, description, status) VALUES (?, ?, ?, ?)",
            (item["id"], item["title"], item.get("description"), item.get("status", "pending")),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="todo with id already exists")
    finally:
        conn.close()
    return {"created": True, "id": item["id"]}


@app.put("/todos/{todo_id}")
async def update_todo(todo_id: str, item: Dict[str, Any]):
    conn = get_db_conn()
    try:
        if not conn.execute("SELECT 1 FROM todos WHERE id=?", (todo_id,)).fetchone():
            raise HTTPException(status_code=404, detail="todo not found")
        updates = []
        params = []
        for key in ("title", "description", "status"):
            if key in item:
                updates.append(f"{key} = ?")
                params.append(item[key])
        if updates:
            params.append(todo_id)
            conn.execute(
                f"UPDATE todos SET {', '.join(updates)}, updated_at = datetime('now') WHERE id = ?",
                params,
            )
            conn.commit()
    finally:
        conn.close()
    return {"updated": True, "id": todo_id}


@app.post("/custom/{plugin_name}")
async def run_custom(plugin_name: str, payload: Dict[str, Any]):
    try:
        safe_name = validate_plugin_name(plugin_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    plugin_path = os.path.join(PLUGIN_DIR, f"{safe_name}.py")
    if not os.path.isfile(plugin_path):
        raise HTTPException(status_code=404, detail="plugin not found")

    spec = importlib.util.spec_from_file_location(safe_name, plugin_path)
    if spec is None or spec.loader is None:
        raise HTTPException(status_code=500, detail="plugin could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "handle"):
        raise HTTPException(status_code=400, detail="plugin must implement handle(payload)")
    try:
        result = module.handle(payload)
        return JSONResponse(content={"result": result})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/")
async def root():
    return {"service": "PROJECT-NAS local backend", "version": "0.1"}
