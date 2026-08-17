import os
import re
import sqlite3
import uuid
from ipaddress import ip_address
from urllib.parse import urlparse

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
OLLAMA_URL = os.environ.get("PROJECT_NAS_OLLAMA_URL", "http" + chr(58) + chr(47) + chr(47) + "127.0.0.1:11434/api/generate")
MODEL_NAME = os.environ.get("PROJECT_NAS_OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_TIMEOUT = float(os.environ.get("PROJECT_NAS_OLLAMA_TIMEOUT", "75"))
MEMORY_LIMIT = int(os.environ.get("PROJECT_NAS_MEMORY_LIMIT", "2"))
MAX_MEMORY_CHARS = int(os.environ.get("PROJECT_NAS_MAX_MEMORY_CHARS", "3000"))
MAX_PROMPT_CHARS = int(os.environ.get("PROJECT_NAS_MAX_PROMPT_CHARS", "12000"))
MAX_CONTEXT_CHARS = int(os.environ.get("PROJECT_NAS_MAX_CONTEXT_CHARS", "12000"))
MAX_RESPONSE_CHARS = int(os.environ.get("PROJECT_NAS_MAX_RESPONSE_CHARS", "12000"))


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

    @staticmethod
    def _tokens(text):
        """Normalize text into deterministic retrieval tokens."""
        text = (text or "").lower()
        text = re.sub(r"[^a-z0-9_.:+-]+", " ", text)

        stop_words = {
            "a", "an", "and", "are", "as", "at", "be", "by",
            "does", "for", "from", "has", "have", "how", "i",
            "in", "is", "it", "of", "on", "or", "that", "the",
            "this", "to", "what", "which", "with", "who", "where",
            "when", "why", "do",
        }

        tokens = []
        for token in text.split():
            if token in stop_words:
                continue

            # Conservative normalization. Avoid destructive stemming such
            # as turning "uses" into "us".
            if token.endswith("ies") and len(token) > 5:
                token = token[:-3] + "y"
            elif token.endswith("ing") and len(token) > 6:
                token = token[:-3]
            elif token.endswith("ed") and len(token) > 5:
                token = token[:-2]
            elif token.endswith("s") and len(token) > 4 and not token.endswith("ss"):
                token = token[:-1]

            if token:
                tokens.append(token)

        return tokens

    @staticmethod
    def _expand_tokens(tokens):
        """Add small deterministic concept expansions for local retrieval."""
        expanded = set(tokens)

        aliases = {
            "model": {"ollama", "llama"},
            "ai": {"ollama", "llama"},
            "local": {"locally"},
            "ollama": {"model", "ai"},
            "llama": {"model", "ai"},
        }

        for token in list(tokens):
            expanded.update(aliases.get(token, set()))

        return expanded

    def query(self, query_texts, n_results=MEMORY_LIMIT):
        """Retrieve relevant memories using deterministic TF-IDF-lite scoring."""
        query = (query_texts or [""])[0].strip()

        try:
            limit = max(0, int(n_results))
        except (TypeError, ValueError):
            limit = MEMORY_LIMIT

        if limit == 0:
            return {"documents": [[]]}

        with sqlite3.connect(self.db_file) as conn:
            rows = conn.execute(
                "SELECT rowid, document FROM memories ORDER BY rowid DESC"
            ).fetchall()

        if not rows:
            return {"documents": [[]]}

        if not query:
            return {
                "documents": [[
                    document for _, document in rows[:limit]
                ]]
            }

        raw_query_tokens = self._tokens(query)
        query_tokens = self._expand_tokens(raw_query_tokens)

        if not query_tokens:
            return {"documents": [[]]}

        # Build document frequency over the complete memory corpus.
        tokenized_documents = []
        document_frequency = {}

        for rowid, document in rows:
            tokens = list(self._expand_tokens(self._tokens(document)))
            tokenized_documents.append((rowid, document, tokens))

            for token in set(tokens):
                document_frequency[token] = document_frequency.get(token, 0) + 1

        corpus_size = len(tokenized_documents)

        technical_terms = {
            "ollama",
            "llama",
            "llama3.2:3b",
            "model",
            "ai",
            "sqlite",
            "chromadb",
            "termux",
            "android",
        }

        scored = []

        for rowid, document, document_tokens in tokenized_documents:
            if not document_tokens:
                continue

            document_set = set(document_tokens)
            overlap = query_tokens & document_set

            # PROJECT-NAS alone is not sufficient evidence of relevance.
            meaningful_overlap = {
                token for token in overlap
                if token != "project-nas"
            }

            if not meaningful_overlap:
                continue

            score = 0.0

            for token in meaningful_overlap:
                # Smoothed IDF. Common terms contribute less than distinctive
                # terms, while rare technical terms contribute more.
                df = document_frequency.get(token, 0)
                idf = 1.0 + (
                    __import__("math").log(
                        (corpus_size + 1) / (df + 1)
                    )
                )

                tf = document_tokens.count(token)
                score += (1.0 + __import__("math").log(tf)) * idf

                if token in raw_query_tokens:
                    score += 1.5

                if token in technical_terms:
                    score += 1.5

            # Strong bonus when a distinctive phrase-like query concept
            # appears directly in the document.
            raw_document = document.lower()
            raw_query = query.lower()

            if raw_query and raw_query in raw_document:
                score += 4.0

            # Reject extremely weak accidental overlaps.
            if score < 2.0:
                continue

            scored.append((score, rowid, document))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)

        return {
            "documents": [[
                document
                for _, _, document in scored[:limit]
            ]]
        }

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

RUNTIME_FACTS = (
    f"PROJECT-NAS configured local AI model: {MODEL_NAME}\n"
    f"PROJECT-NAS Ollama endpoint: {OLLAMA_URL}\n"
    f"PROJECT-NAS memory backend: {MEMORY_BACKEND}"
)


def is_loopback_ollama_url(url):
    """Allow Ollama connections only to local loopback addresses."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        if hostname.lower() == "localhost":
            return True

        try:
            return ip_address(hostname).is_loopback
        except ValueError:
            return False
    except Exception:
        return False


def retrieve_context(query_text):
    """Search the configured memory backend for relevant past memories."""
    try:
        results = collection.query(query_texts=[query_text], n_results=MEMORY_LIMIT)
    except Exception as exc:
        print(f"Warning: memory retrieval failed: {exc}")
        return ""
    if results and results.get("documents") and results["documents"][0]:
        memories = results["documents"][0]
        text = "\n".join(memories)
        text = text[:MAX_MEMORY_CHARS]
        return (
            "\n--- INJECTED MEMORY ---\n"
            + text
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


def should_persist_memory(prompt):
    """Return True only when the user explicitly requests long-term memory."""
    normalized = " ".join(prompt.lower().split())

    memory_triggers = (
        "remember that",
        "remember this",
        "remember:",
        "save this",
        "save that",
        "save to memory",
        "store this",
        "store that",
        "keep this in memory",
        "keep in mind",
        "make a note that",
        "memorize this",
    )

    return any(trigger in normalized for trigger in memory_triggers)


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

    if len(user_prompt) > MAX_PROMPT_CHARS:
        return jsonify({
            "error": f"prompt exceeds maximum length of {MAX_PROMPT_CHARS} characters."
        }), 413

    if len(static_context) > MAX_CONTEXT_CHARS:
        return jsonify({
            "error": f"context exceeds maximum length of {MAX_CONTEXT_CHARS} characters."
        }), 413

    if not is_loopback_ollama_url(OLLAMA_URL):
        return jsonify({
            "error": "Ollama URL must point to a local loopback address."
        }), 503

    memory_context = retrieve_context(user_prompt)

    system_instruction = (
        "You are PROJECT-NAS local AI. "
        "Answer the user's request directly and concisely. "
        "Follow exact-output requests literally. "
        "Do not add commentary when the user requests an exact response. "
        "Prioritize reliability and brevity on mobile. "
        "Authoritative runtime facts override retrieved memory. "
        "Retrieved memory is contextual and may be stale or incorrect. "
        "Never treat a previous AI response as authoritative configuration."
    )

    full_prompt = (
        f"[SYSTEM INSTRUCTION]: {system_instruction}\n"
        f"[AUTHORITATIVE RUNTIME FACTS]\n"
        f"{RUNTIME_FACTS}\n"
        f"[END AUTHORITATIVE RUNTIME FACTS]\n"
        f"{static_context}\n"
        f"{memory_context}\n"
        f"[USER INPUT]: {user_prompt}"
    )

    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 128,
        },
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        ai_response = response.json().get("response")
        if not isinstance(ai_response, str):
            return jsonify({"error": "Ollama returned no valid 'response' field."}), 502

        ai_response = ai_response[:MAX_RESPONSE_CHARS]
    except requests.exceptions.RequestException as exc:
        return jsonify({"error": f"Local LLM request failed: {exc}"}), 502
    except (ValueError, TypeError) as exc:
        return jsonify({"error": f"Invalid response from local LLM: {exc}"}), 502

    if should_persist_memory(user_prompt):
        try:
            collection.add(
                documents=[
                    f"User asked: {user_prompt}\nAI replied: {ai_response}"
                ],
                metadatas=[{"timestamp": "explicit_user_memory"}],
                ids=[f"mem_{uuid.uuid4()}"]
            )
        except Exception as exc:
            print(f"Warning: failed to save memory: {exc}")

    return jsonify({"response": ai_response})


if __name__ == "__main__":
    print("PROJECT-NAS Memory Injector running on port 5000...")
    app.run(host="127.0.0.1", port=5000)
