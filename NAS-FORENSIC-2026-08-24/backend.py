from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
import json, os, sqlite3, time, subprocess, uuid, re, tempfile
from typing import Any, Dict, List
import requests

CHAT_TIMEOUT_SECONDS = 120
MAX_CHAT_PROMPT_CHARS = 4000
MAX_CHAT_CONTEXT_CHARS = 8000
MAX_CHAT_RESPONSE_CHARS = 2000
MAX_TODO_ID_CHARS = 64
MAX_TODO_TEXT_CHARS = 500
MAX_TODO_STATUS_CHARS = 32

app = FastAPI(title="PROJECT-NAS Backend")

# ============ Memory ============
class Memory:
    def __init__(self, db_path="memory.sqlite3"):
        self.db_path = os.path.join(os.path.dirname(__file__), db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT,
            value TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key)')
        conn.commit(); conn.close()
    def store(self, key, value):
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO memories (key, value) VALUES (?, ?)", (key, value))
        conn.commit(); conn.close()
    def retrieve(self, query, limit=3):
        conn = sqlite3.connect(self.db_path)
        keywords = [w for w in query.lower().split() if len(w)>2]
        if not keywords:
            rows = conn.execute(
                "SELECT key, value FROM memories WHERE key LIKE ? OR value LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{query}%", f"%{query}%", limit)
            ).fetchall()
        else:
            conditions = ["key LIKE ?" for _ in keywords] + ["value LIKE ?" for _ in keywords]
            params = [f"%{kw}%" for kw in keywords]*2 + [limit]
            rows = conn.execute(
                "SELECT key, value FROM memories WHERE " + " OR ".join(conditions) + " ORDER BY timestamp DESC LIMIT ?",
                params
            ).fetchall()
        conn.close()
        return [f"{row[0]}: {row[1]}" for row in rows]
memory = Memory()

# ============ DB helpers ============
def get_db_conn():
    conn = sqlite3.connect("session.db")
    conn.execute("CREATE TABLE IF NOT EXISTS todos (id TEXT PRIMARY KEY, text TEXT, status TEXT, created_at TEXT, updated_at TEXT)")
    return conn

# ============ Chat worker ============
def _call_chat_worker(prompt: str, context: str) -> dict[str, Any]:
    if "remember that" in prompt.lower():
        parts = prompt.lower().split("remember that", 1)
        if len(parts) > 1 and parts[1].strip():
            fact = parts[1].strip()
            memory.store(fact, prompt)
            return {"response": f"Okay, I'll remember: {fact}"}
    retrieved = memory.retrieve(prompt, limit=3)
    memory_context = "Relevant memories:\n" + "\n".join(retrieved) + "\n\n" if retrieved else ""
    ollama_url = "http://100.119.61.2:11434/v1"   # hardcoded for stability
    model = "llama3.2:1b"
    full_prompt = f"{memory_context}{context}\n\n{prompt}" if context else f"{memory_context}{prompt}"
    payload = {"model": model, "messages": [{"role": "user", "content": full_prompt}], "stream": False}
    try:
        response = requests.post(f"{ollama_url}/chat/completions", json=payload, timeout=CHAT_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            memory.store(prompt, content)
            return {"response": content[:MAX_CHAT_RESPONSE_CHARS]}
        else:
            raise HTTPException(502, "No response from Ollama")
    except requests.exceptions.RequestException as e:
        raise HTTPException(503, f"Ollama unavailable: {str(e)}")

# ============ Routes (define before static mount) ============
@app.get("/prompt")
async def prompt_get(prompt: str):
    return _call_chat_worker(prompt, "")

@app.post("/chat")
async def chat(payload: Dict[str, Any]):
    if not isinstance(payload, dict):
        raise HTTPException(400, "request body must be an object")
    prompt = payload.get("prompt")
    if not prompt:
        raise HTTPException(400, "Missing prompt field")
    context = payload.get("context", "")
    return _call_chat_worker(prompt, context)

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/todos")
async def list_todos():
    conn = get_db_conn()
    try:
        rows = conn.execute("SELECT id, text, status, created_at, updated_at FROM todos ORDER BY created_at DESC").fetchall()
        return [{"id": r[0], "text": r[1], "status": r[2], "created_at": r[3], "updated_at": r[4]} for r in rows]
    finally: conn.close()

@app.post("/todos")
async def create_todo(payload: Dict[str, Any]):
    text = payload.get("text", "").strip()
    if not text:
        raise HTTPException(400, "Missing text field")
    todo_id = str(uuid.uuid4())[:8]
    conn = get_db_conn()
    try:
        conn.execute("INSERT INTO todos (id, text, status, created_at, updated_at) VALUES (?, ?, ?, datetime('now'), datetime('now'))",
                     (todo_id, text, "pending"))
        conn.commit()
        return {"id": todo_id, "text": text, "status": "pending"}
    finally: conn.close()

@app.put("/todos/{todo_id}")
async def update_todo(todo_id: str, payload: Dict[str, Any]):
    status = payload.get("status", "").strip()
    if status not in ["pending", "done"]:
        raise HTTPException(400, "status must be pending or done")
    conn = get_db_conn()
    try:
        if not conn.execute("SELECT 1 FROM todos WHERE id=?", (todo_id,)).fetchone():
            raise HTTPException(404, "todo not found")
        conn.execute("UPDATE todos SET status=?, updated_at=datetime('now') WHERE id=?", (status, todo_id))
        conn.commit()
        return {"updated": True, "id": todo_id}
    finally: conn.close()

@app.get("/")
async def root():
    return {"service": "PROJECT-NAS local backend", "version": "1.0"}

# ============ SKILL LOADER ============
def list_skills():
    skills = []
    skills_dir = "skills/"
    if os.path.exists(skills_dir):
        for skill in os.listdir(skills_dir):
            if os.path.isdir(os.path.join(skills_dir, skill)):
                skills.append(skill)
    return skills

@app.get("/list_skills")
async def get_skills():
    return {"skills": list_skills()}

# ============ AUTOPILOT ============
@app.post("/autopilot")
async def autopilot(task: Dict[str, Any]):
    task_description = task.get("task", "").strip()
    if not task_description:
        raise HTTPException(400, "Missing task description")
    system_prompt = "You are BOB, the autonomous builder. Return ONLY the Python code, no explanation."
    full_prompt = f"{system_prompt}\n\nTask: {task_description}\n\nPython code:"
    try:
        response = _call_chat_worker(full_prompt, "")
        code = response.get("response", "")
        code = re.sub(r'^```python\s*', '', code)
        code = re.sub(r'\s*```$', '', code)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        result = subprocess.run(['python3', temp_path], capture_output=True, text=True, timeout=30)
        os.unlink(temp_path)
        return {
            "task": task_description,
            "code": code,
            "output": result.stdout,
            "error": result.stderr if result.stderr else None,
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Execution timed out")
    except Exception as e:
        raise HTTPException(500, f"Autopilot error: {str(e)}")

# ============ SELF-BUILD ============
@app.post("/self_build")
async def self_build():
    import subprocess, tempfile, time, re, os
    subprocess.run(["git", "pull"], capture_output=True)
    prompt = "Analyze the codebase and suggest a small improvement. Return a unified diff patch."
    response = _call_chat_worker(prompt, "")
    patch = response.get("response", "")
    if not patch:
        return {"status": "no_patch", "message": "No improvement generated."}
    try:
        subprocess.run(["patch", "-p1"], input=patch.encode(), capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        return {"status": "patch_failed", "error": str(e)}
    test_result = subprocess.run(["python", "-m", "pytest", "tests/"], capture_output=True, text=True)
    if test_result.returncode != 0:
        subprocess.run(["git", "checkout", "--", "."])
        return {"status": "tests_failed", "output": test_result.stdout + test_result.stderr}
    subprocess.run(["git", "add", "."])
    commit_msg = f"Self-build: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    subprocess.run(["git", "commit", "-m", commit_msg])
    subprocess.run(["git", "push"])
    return {"status": "success", "message": "Improvement applied and committed."}

# ============ Static files (mount last) ============
app.mount("/", StaticFiles(directory="static", html=True))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
