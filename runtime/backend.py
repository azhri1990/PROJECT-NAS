from fastapi import FastAPI, HTTPException
import json
import os
import sqlite3
from ipaddress import ip_address
from typing import Any, Dict
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from runtime.git_reader import get_repo_info
from runtime.tool_gateway import build_default_gateway

app = FastAPI(title="PROJECT-NAS Local Backend")

MAX_TODO_ID_CHARS = 128
MAX_TODO_TITLE_CHARS = 500
MAX_TODO_DESCRIPTION_CHARS = 4000
MAX_TODO_STATUS_CHARS = 64
MAX_CHAT_PROMPT_CHARS = int(os.environ.get("PROJECT_NAS_MAX_PROMPT_CHARS", "12000"))
MAX_CHAT_CONTEXT_CHARS = int(os.environ.get("PROJECT_NAS_MAX_CONTEXT_CHARS", "12000"))
MAX_CHAT_RESPONSE_CHARS = int(os.environ.get("PROJECT_NAS_MAX_RESPONSE_CHARS", "12000"))
CHAT_TIMEOUT_SECONDS = float(os.environ.get("PROJECT_NAS_CHAT_TIMEOUT", "90"))
ALLOWED_TODO_STATUSES = frozenset({"pending", "in_progress", "completed", "cancelled"})
ALLOWED_CHAT_METADATA = frozenset({"model", "budget", "memory"})


def resolve_session_db() -> str:
    configured = os.environ.get("PROJECT_NAS_SESSION_DB")
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "session.db"))


SESSION_DB = resolve_session_db()

PROMPT_PATHS = [
    os.path.join(os.path.dirname(__file__), "..", "ai", "MASTER_PROMPT.md"),
    os.path.join(os.path.dirname(__file__), "..", "ai", "AI_OPERATING_SYSTEM_SUMMARY.md"),
]


def load_prompt() -> Dict[str, Any]:
    for path in PROMPT_PATHS:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                return {"path": path, "prompt": handle.read()}
    return {"path": None, "prompt": ""}


def read_prompt(max_chars: int = 12000) -> dict[str, Any]:
    loaded = load_prompt()
    content = loaded["prompt"]
    bounded = content[:max_chars]
    return {
        "path": loaded["path"],
        "content": bounded,
        "chars": len(bounded),
        "truncated": len(content) > len(bounded),
    }


def run_git_info(commits: int = 10) -> Dict[str, Any]:
    return get_repo_info(commits)


def _probe_http(url: str) -> dict[str, Any]:
    try:
        request = Request(url, method="GET")
        with urlopen(request, timeout=2) as response:
            return {"ok": 200 <= response.status < 300, "status_code": response.status}
    except HTTPError as exc:
        return {"ok": False, "status_code": exc.code, "error": str(exc.reason)}
    except (URLError, OSError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)}


def _probe_ollama() -> dict[str, Any]:
    base = os.environ.get("PROJECT_NAS_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    result = _probe_http(base.rstrip("/") + "/api/tags")
    result["url"] = base
    return result


def _probe_memory_api() -> dict[str, Any]:
    url = os.environ.get("PROJECT_NAS_MEMORY_HEALTH_URL", "http://127.0.0.1:5000/health")
    result = _probe_http(url)
    result["url"] = url
    return result


def _probe_memory_sqlite() -> dict[str, Any]:
    db_path = os.environ.get(
        "PROJECT_NAS_MEMORY_DB",
        os.path.join(os.path.dirname(__file__), "claude-mem-db", "memory.sqlite3"),
    )
    db_path = os.path.abspath(os.path.expanduser(db_path))
    if not os.path.splitext(db_path)[1]:
        db_path = os.path.join(db_path, "memory.sqlite3")
    if not os.path.isfile(db_path):
        return {"ok": False, "path": db_path, "error": "database file not found"}
    try:
        uri = "file:" + db_path.replace("\\", "/") + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        return {"ok": True, "path": db_path, "records": int(count)}
    except sqlite3.Error as exc:
        return {"ok": False, "path": db_path, "error": str(exc)}


def _probe_repository() -> dict[str, Any]:
    try:
        info = get_repo_info(1)
        ok = info.get("branch") not in {None, "unknown"}
        return {"ok": ok, "branch": info.get("branch"), "recent_commits": len(info.get("recent_commits", []))}
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


def _probe_model() -> dict[str, Any]:
    base = os.environ.get("PROJECT_NAS_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    configured = os.environ.get("PROJECT_NAS_OLLAMA_MODEL", "llama3.2:3b")
    preferred = [configured, "llama3.2:3b", "llama3.2:1b", "llama3.1:8b"]
    try:
        request = Request(base.rstrip("/") + "/api/tags", method="GET")
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        models = sorted({item.get("name") for item in payload.get("models", []) if isinstance(item, dict) and item.get("name")})
        selected = next((name for name in preferred if name in models), models[0] if models else None)
        return {"ok": selected is not None, "name": selected or configured, "configured": configured, "fallback": selected is not None and selected != configured}
    except (HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
        return {"ok": False, "name": configured, "configured": configured, "fallback": False, "error": str(exc)}


def health_report() -> dict[str, Any]:
    components = {
        "ollama": _probe_ollama(),
        "memory_api": _probe_memory_api(),
        "memory_sqlite": _probe_memory_sqlite(),
        "repository": _probe_repository(),
        "model": _probe_model(),
    }
    core = ("ollama", "memory_api", "model")
    if any(not components[name].get("ok") for name in core):
        status = "unavailable"
    elif any(not component.get("ok") for component in components.values()):
        status = "degraded"
    else:
        status = "healthy"
    return {"status": status, "components": components}


def _bounded_text(value: Any, field: str, maximum: int, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise HTTPException(status_code=400, detail=f"{field} is required")
        return None
    if not isinstance(value, str):
        raise HTTPException(status_code=400, detail=f"{field} must be a string")
    value = value.strip()
    if required and not value:
        raise HTTPException(status_code=400, detail=f"{field} is required")
    if len(value) > maximum:
        raise HTTPException(status_code=413, detail=f"{field} exceeds maximum length of {maximum} characters")
    return value


def _validate_todo_create(item: Dict[str, Any]) -> dict[str, str | None]:
    if not isinstance(item, dict):
        raise HTTPException(status_code=400, detail="request body must be an object")
    allowed = {"id", "title", "description", "status"}
    unsupported = set(item) - allowed
    if unsupported:
        raise HTTPException(status_code=400, detail=f"unsupported todo fields: {', '.join(sorted(unsupported))}")
    todo_id = _bounded_text(item.get("id"), "id", MAX_TODO_ID_CHARS, required=True)
    title = _bounded_text(item.get("title"), "title", MAX_TODO_TITLE_CHARS, required=True)
    description = _bounded_text(item.get("description"), "description", MAX_TODO_DESCRIPTION_CHARS)
    status = _bounded_text(item.get("status", "pending"), "status", MAX_TODO_STATUS_CHARS, required=True)
    if status not in ALLOWED_TODO_STATUSES:
        raise HTTPException(status_code=400, detail="status must be one of: pending, in_progress, completed, cancelled")
    return {"id": todo_id, "title": title, "description": description, "status": status}


def _validate_todo_update(item: Dict[str, Any]) -> dict[str, str | None]:
    if not isinstance(item, dict):
        raise HTTPException(status_code=400, detail="request body must be an object")
    allowed = {"title", "description", "status"}
    unsupported = set(item) - allowed
    if unsupported:
        raise HTTPException(status_code=400, detail=f"unsupported todo fields: {', '.join(sorted(unsupported))}")
    if not item:
        raise HTTPException(status_code=400, detail="at least one todo field is required")
    result: dict[str, str | None] = {}
    if "title" in item:
        result["title"] = _bounded_text(item["title"], "title", MAX_TODO_TITLE_CHARS, required=True)
    if "description" in item:
        result["description"] = _bounded_text(item["description"], "description", MAX_TODO_DESCRIPTION_CHARS)
    if "status" in item:
        status = _bounded_text(item["status"], "status", MAX_TODO_STATUS_CHARS, required=True)
        if status not in ALLOWED_TODO_STATUSES:
            raise HTTPException(status_code=400, detail="status must be one of: pending, in_progress, completed, cancelled")
        result["status"] = status
    return result


def _is_loopback_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        hostname = parsed.hostname.lower()
        if hostname == "localhost":
            return True
        try:
            return ip_address(hostname).is_loopback
        except ValueError:
            return False
    except (TypeError, ValueError):
        return False


def _chat_worker_url() -> str:
    url = os.environ.get("PROJECT_NAS_CHAT_WORKER_URL", "http://127.0.0.1:5000/chat")
    if not _is_loopback_url(url):
        raise HTTPException(status_code=503, detail="chat worker must use a loopback URL")
    return url


def _call_chat_worker(prompt: str, context: str) -> dict[str, Any]:
    worker_url = _chat_worker_url()
    payload = json.dumps({"context": context, "prompt": prompt}).encode("utf-8")
    request = Request(worker_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=CHAT_TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_CHAT_RESPONSE_CHARS + 4096)
            if response.status < 200 or response.status >= 300:
                raise HTTPException(status_code=502, detail="local chat worker returned an unsuccessful status")
    except HTTPException:
        raise
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="local chat worker is unavailable") from exc
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="local chat worker returned invalid JSON") from exc
    if not isinstance(data, dict) or not isinstance(data.get("response"), str):
        raise HTTPException(status_code=502, detail="local chat worker returned no valid response")
    result: dict[str, Any] = {"response": data["response"][:MAX_CHAT_RESPONSE_CHARS]}
    for key in ALLOWED_CHAT_METADATA:
        value = data.get(key)
        if isinstance(value, (str, int, float, bool, dict, list)):
            result[key] = value
    return result


TOOL_GATEWAY = build_default_gateway(run_git_info)


def get_db_conn():
    db_path = resolve_session_db()
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS todos (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""")
    conn.commit()
    return conn


@app.get("/health")
async def get_health():
    return health_report()


@app.get("/prompt")
async def get_prompt():
    return read_prompt()


@app.post("/chat")
async def chat(payload: Dict[str, Any]):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="request body must be an object")
    allowed = {"prompt", "context"}
    unsupported = set(payload) - allowed
    if unsupported:
        raise HTTPException(status_code=400, detail=f"unsupported chat fields: {', '.join(sorted(unsupported))}")
    prompt = _bounded_text(payload.get("prompt"), "prompt", MAX_CHAT_PROMPT_CHARS, required=True)
    context = _bounded_text(payload.get("context", ""), "context", MAX_CHAT_CONTEXT_CHARS) or ""
    return _call_chat_worker(prompt, context)


@app.get("/progress")
async def progress(commits: int = 10):
    return TOOL_GATEWAY.execute("status.progress", {"commits": commits})


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
        rows = conn.execute("SELECT id, title, description, status, created_at, updated_at FROM todos ORDER BY created_at").fetchall()
    finally:
        conn.close()
    return {"todos": [{"id": row[0], "title": row[1], "description": row[2], "status": row[3], "created_at": row[4], "updated_at": row[5]} for row in rows]}


@app.post("/todos")
async def create_todo(item: Dict[str, Any]):
    validated = _validate_todo_create(item)
    conn = get_db_conn()
    try:
        conn.execute("INSERT INTO todos (id, title, description, status) VALUES (?, ?, ?, ?)", (validated["id"], validated["title"], validated["description"], validated["status"]))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="todo with id already exists")
    finally:
        conn.close()
    return {"created": True, "id": validated["id"]}


@app.put("/todos/{todo_id}")
async def update_todo(todo_id: str, item: Dict[str, Any]):
    todo_id = _bounded_text(todo_id, "todo_id", MAX_TODO_ID_CHARS, required=True)
    validated = _validate_todo_update(item)
    conn = get_db_conn()
    try:
        if not conn.execute("SELECT 1 FROM todos WHERE id=?", (todo_id,)).fetchone():
            raise HTTPException(status_code=404, detail="todo not found")
        updates = [f"{key} = ?" for key in validated]
        params = list(validated.values())
        params.append(todo_id)
        conn.execute(f"UPDATE todos SET {', '.join(updates)}, updated_at = datetime('now') WHERE id = ?", params)
        conn.commit()
    finally:
        conn.close()
    return {"updated": True, "id": todo_id}


@app.get("/")
async def root():
    return {"service": "PROJECT-NAS local backend", "version": "0.1"}
