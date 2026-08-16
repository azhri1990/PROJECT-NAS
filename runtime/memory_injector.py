import os
import sqlite3
import uuid

import requests
from flask import Flask, jsonify, request

try:
    import chromadb
except ImportError:  # Android/Termux-friendly fallback
    chromadb = None

app = Flask(__name__)

# Keep runtime state beside this module so the service is independent of cwd.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("PROJECT_NAS_MEMORY_DB", os.path.join(BASE_DIR, "claude-mem-db"))
OLLAMA_URL = os.environ.get("PROJECT_NAS_OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.environ.get("PROJECT_NAS_OLLAMA_MODEL", "llama3.2:3b")


class SQLiteMemoryCollection:
    """Small built-in memory adapter for platforms where ChromaDB cannot install."""

    def __init__(self, path):
        if os.path.splitext(path)[1]:
            db_file = path
            parent = os.path.dirname(path)
        else:
            parent = path
            db_file = os.path.join(path, "memory.sqlite3")
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.db_file = db_file
        with sqlite3.connect(self.db_file) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS memories ("
                "id TEXT PRIMARY KEY, document TEXT NOT NULL, metadata TEXT)"
            )
            conn.commit()

    def query(self, query_texts, n_results=3):
        query = (query_texts or [""])[0].strip()
        with sqlite3.connect(self.db_file) as conn:
            if query:
                rows = conn.execute(
                    "SELECT document FROM memories WHERE document LIKE ? "
                    "ORDER BY rowid DESC LIMIT ?",
                    (f"%{query}%", n_results),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT document FROM memories ORDER BY rowid DESC LIMIT ?",
                    (n_results,),
                ).fetchall()
        return {"documents": [[row[0] for row in rows]]}

    def add(self, documents, metadatas=None, ids=None):
        documents = documents or []
        ids = ids or [f"mem_{uuid.uuid4()}" for _ in documents]
        metadatas = metadatas or [{} for _ in documents]
        with sqlite3.connect(self.db_file) as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO memories (id, document, metadata) VALUES (?, ?, ?)",
                [(item_id, document, str(metadata))
                 for item_id, document, metadata in zip(ids, documents, metadatas)],
            )
            conn.commit()


if chromadb is not None:
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(name="project_nas_memory")
    MEMORY_BACKEND = "chromadb"
else:
    collection = SQLiteMemoryCollection(DB_PATH)
    MEMORY_BACKEND = "sqlite"


def retrieve_context(query_text):
    """Search the configured memory backend for relevant past memories."""
    try:
        results = collection.query(query_texts=[query_text], n_results=3)
    except Exception as exc:
        print(f"Warning: memory retrieval failed: {exc}")
        return ""
    if results and results.get("documents") and results["documents"][0]:
        return (
            "\n--- INJECTED MEMORY ---\n"
            + "\n".join(results["documents"][0])
            + "\n--- END MEMORY ---\n"
        )
    return ""


@app.route("/health", methods=["GET"])
def health():
    """Expose local service configuration without leaking memory contents."""
    return jsonify({
        "status": "ok",
        "model": MODEL_NAME,
        "ollama_url": OLLAMA_URL,
        "memory_backend": MEMORY_BACKEND,
    })


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Request body must be valid JSON."}), 400

    user_prompt = data.get("prompt")
    if not isinstance(user_prompt, str) or not user_prompt.strip():
        return jsonify({"error": "Missing 'prompt' field."}), 400

    static_context = data.get("context", "") or ""
    if not isinstance(static_context, str):
        return jsonify({"error": "'context' must be a string."}), 400

    memory_context = retrieve_context(user_prompt)
    full_prompt = (
        f"{static_context}\n{memory_context}\n"
        f"[USER INPUT]: {user_prompt}\n"
        f"[SYSTEM INSTRUCTION]: You are the Omni-Coach. Answer directly, "
        f"apply the 80/20 rule, and give the brutal truth."
    )

    payload = {"model": MODEL_NAME, "prompt": full_prompt, "stream": False}

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        ai_response = response.json().get("response")
        if not isinstance(ai_response, str):
            return jsonify({"error": "Ollama returned no valid 'response' field."}), 502
    except requests.exceptions.RequestException as exc:
        return jsonify({"error": f"Local LLM request failed: {exc}"}), 502
    except (ValueError, TypeError) as exc:
        return jsonify({"error": f"Invalid response from local LLM: {exc}"}), 502

    try:
        collection.add(
            documents=[f"User asked: {user_prompt}\nAI replied: {ai_response}"],
            metadatas=[{"timestamp": "session_auto"}],
            ids=[f"mem_{uuid.uuid4()}"]
        )
    except Exception as exc:
        print(f"Warning: failed to save memory: {exc}")

    return jsonify({"response": ai_response})


if __name__ == "__main__":
    print("PROJECT-NAS Memory Injector running on port 5000...")
    app.run(host="127.0.0.1", port=5000)
