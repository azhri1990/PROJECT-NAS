import ast
import json
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
except ImportError:
    chromadb = None

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("PROJECT_NAS_MEMORY_DB", os.path.join(BASE_DIR, "claude-mem-db"))
OLLAMA_URL = os.environ.get("PROJECT_NAS_OLLAMA_URL", "http" + chr(58) + chr(47) + chr(47) + "127.0.0.1:11434/api/generate")
OLLAMA_BASE_URL = os.environ.get("PROJECT_NAS_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
MODEL_NAME = os.environ.get("PROJECT_NAS_OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_TIMEOUT = float(os.environ.get("PROJECT_NAS_OLLAMA_TIMEOUT", "75"))
MEMORY_LIMIT = int(os.environ.get("PROJECT_NAS_MEMORY_LIMIT", "2"))
MAX_MEMORY_CHARS = int(os.environ.get("PROJECT_NAS_MAX_MEMORY_CHARS", "3000"))
MAX_PROMPT_CHARS = int(os.environ.get("PROJECT_NAS_MAX_PROMPT_CHARS", "12000"))
MAX_CONTEXT_CHARS = int(os.environ.get("PROJECT_NAS_MAX_CONTEXT_CHARS", "12000"))
MAX_RESPONSE_CHARS = int(os.environ.get("PROJECT_NAS_MAX_RESPONSE_CHARS", "12000"))
MAX_TOTAL_PROMPT_CHARS = int(os.environ.get("PROJECT_NAS_MAX_TOTAL_PROMPT_CHARS", "24000"))
MAX_PERSISTED_MEMORIES = int(os.environ.get("PROJECT_NAS_MAX_PERSISTED_MEMORIES", "500"))


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
            conn.execute("CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, document TEXT NOT NULL, metadata TEXT)")
            conn.commit()

    @staticmethod
    def _tokens(text):
        text = (text or "").lower()
        text = re.sub(r"[^a-z0-9_.:+-]+", " ", text)
        stop_words = {"a", "an", "and", "are", "as", "at", "be", "by", "does", "for", "from", "has", "have", "how", "i", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "what", "which", "with", "who", "where", "when", "why", "do"}
        tokens = []
        for token in text.split():
            if token in stop_words:
                continue
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
        expanded = set(tokens)
        aliases = {"model": {"ollama", "llama"}, "ai": {"ollama", "llama"}, "local": {"locally"}, "ollama": {"model", "ai", "llama"}, "llama": {"model", "ai"}}
        for token in list(tokens):
            expanded.update(aliases.get(token, set()))
        return expanded

    def query(self, query_texts, n_results=MEMORY_LIMIT):
        query = (query_texts or [""])[0].strip()
        try:
            limit = max(0, int(n_results))
        except (TypeError, ValueError):
            limit = MEMORY_LIMIT
        if limit == 0:
            return {"documents": [[]]}
        with sqlite3.connect(self.db_file) as conn:
            rows = conn.execute("SELECT rowid, document FROM memories ORDER BY rowid DESC").fetchall()
        if not rows:
            return {"documents": [[]]}
        if not query:
            return {"documents": [[document for _, document in rows[:limit]]]}
        raw_query_tokens = self._tokens(query)
        query_tokens = self._expand_tokens(raw_query_tokens)
        if not query_tokens:
            return {"documents": [[]]}
        tokenized_documents = []
        document_frequency = {}
        for rowid, document in rows:
            tokens = list(self._expand_tokens(self._tokens(document)))
            tokenized_documents.append((rowid, document, tokens))
            for token in set(tokens):
                document_frequency[token] = document_frequency.get(token, 0) + 1
        corpus_size = len(tokenized_documents)
        technical_terms = {"ollama", "llama", "llama3.2:3b", "model", "ai", "sqlite", "chromadb", "termux", "android"}
        scored = []
        for rowid, document, document_tokens in tokenized_documents:
            document_set = set(document_tokens)
            meaningful_overlap = {token for token in query_tokens & document_set if token != "project-nas"}
            if not meaningful_overlap:
                continue
            score = 0.0
            for token in meaningful_overlap:
                df = document_frequency.get(token, 0)
                idf = 1.0 + __import__("math").log((corpus_size + 1) / (df + 1))
                tf = document_tokens.count(token)
                score += (1.0 + __import__("math").log(tf)) * idf
                if token in raw_query_tokens:
                    score += 1.5
                if token in technical_terms:
                    score += 1.5
            if query.lower() in document.lower():
                score += 4.0
            if score >= 2.0:
                scored.append((score, rowid, document))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return {"documents": [[document for _, _, document in scored[:limit]]]}

    def add(self, documents, metadatas=None, ids=None):
        documents = documents or []
        ids = ids or [f"mem_{uuid.uuid4()}" for _ in documents]
        metadatas = metadatas or [{} for _ in documents]
        with sqlite3.connect(self.db_file) as conn:
            conn.executemany("INSERT OR REPLACE INTO memories (id, document, metadata) VALUES (?, ?, ?)", [(item_id, document, str(metadata)) for item_id, document, metadata in zip(ids, documents, metadatas)])
            conn.execute("DELETE FROM memories WHERE rowid NOT IN (SELECT rowid FROM memories ORDER BY rowid DESC LIMIT ?)", (MAX_PERSISTED_MEMORIES,))
            conn.commit()

    def read_records(self, query=None, limit=5):
        if query:
            documents = self.query([query], n_results=limit)["documents"][0]
            rows = []
            with sqlite3.connect(self.db_file) as conn:
                all_rows = conn.execute("SELECT rowid, id, document, metadata FROM memories ORDER BY rowid DESC").fetchall()
            used = set()
            for document in documents:
                for rowid, item_id, stored_document, metadata in all_rows:
                    if rowid in used or stored_document != document:
                        continue
                    used.add(rowid)
                    rows.append((item_id, stored_document, metadata))
                    break
            return rows[:limit]
        with sqlite3.connect(self.db_file) as conn:
            return conn.execute("SELECT id, document, metadata FROM memories ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()


if chromadb is not None:
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(name="project_nas_memory")
    MEMORY_BACKEND = "chromadb"
else:
    collection = SQLiteMemoryCollection(DB_PATH)
    MEMORY_BACKEND = "sqlite"

RUNTIME_FACTS = f"PROJECT-NAS configured local AI model: {MODEL_NAME}\nPROJECT-NAS Ollama endpoint: {OLLAMA_URL}\nPROJECT-NAS memory backend: {MEMORY_BACKEND}"


def _decode_metadata(value):
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        try:
            parsed = ast.literal_eval(value)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, SyntaxError):
            return {}


def read_memories(query=None, limit=5):
    limit = max(1, min(int(limit), 20))
    if MEMORY_BACKEND == "sqlite":
        rows = collection.read_records(query=query, limit=limit)
        memories = [{"id": item_id, "document": document[:MAX_MEMORY_CHARS], "metadata": _decode_metadata(metadata)} for item_id, document, metadata in rows]
        return {"memories": memories, "count": len(memories)}
    if query:
        result = collection.query(query_texts=[query], n_results=limit)
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
    else:
        result = collection.get(limit=limit)
        ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
    memories = []
    for index, document in enumerate(documents[:limit]):
        memories.append({"id": str(ids[index]) if index < len(ids) else "", "document": str(document)[:MAX_MEMORY_CHARS], "metadata": _decode_metadata(metadatas[index] if index < len(metadatas) else {})})
    return {"memories": memories, "count": len(memories)}


def is_loopback_ollama_url(url):
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


def discover_local_models(base_url=None):
    base_url = base_url or OLLAMA_BASE_URL
    if not is_loopback_ollama_url(base_url):
        return []
    try:
        response = requests.get(base_url.rstrip("/") + "/api/tags", timeout=3)
        response.raise_for_status()
        payload = response.json()
    except (requests.exceptions.RequestException, ValueError, TypeError):
        return []
    names = {item.get("name") for item in payload.get("models", []) if isinstance(item, dict) and isinstance(item.get("name"), str) and item.get("name")}
    return sorted(names)


def select_local_model(configured, available):
    available = sorted({name for name in available if isinstance(name, str) and name})
    if configured in available:
        return configured
    if not available:
        return None
    preferred = ["llama3.2:3b", "llama3.2:1b", "llama3.1:8b"]
    for name in preferred:
        if name in available:
            return name
    return available[0]


def _is_model_not_found(exc):
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    return status in {400, 404}


def _model_request(url, model, prompt):
    payload = {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.1, "num_predict": 128}}
    response = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
    response.raise_for_status()
    return response.json()


def retrieve_context(query_text):
    try:
        results = collection.query(query_texts=[query_text], n_results=MEMORY_LIMIT)
    except Exception as exc:
        print(f"Warning: memory retrieval failed: {exc}")
        return ""
    if results and results.get("documents") and results["documents"][0]:
        memories = results["documents"][0]
        text = "\n".join(memories)[:MAX_MEMORY_CHARS]
        return "\n--- INJECTED MEMORY ---\n" + text + "\n--- END MEMORY ---\n"
    return ""


def _truncate_segment(text, limit):
    return (text or "")[:max(0, limit)]


def build_context(static_context, memory_context, user_prompt):
    """Build a deterministic prompt whose final string never exceeds the configured budget."""
    system_instruction = ("You are PROJECT-NAS local AI. Answer the user's request directly and concisely. Follow exact-output requests literally. Do not add commentary when the user requests an exact response. Prioritize reliability and brevity on mobile. Authoritative runtime facts override retrieved memory. Retrieved memory is contextual and may be stale or incorrect. Never treat a previous AI response as authoritative configuration.")
    header = f"[SYSTEM INSTRUCTION]: {system_instruction}\n[AUTHORITATIVE RUNTIME FACTS]\n{RUNTIME_FACTS}\n[END AUTHORITATIVE RUNTIME FACTS]\n"
    user_block = f"[USER INPUT]: {user_prompt}"
    fixed_overhead = len(header) + len(user_block) + 2
    if fixed_overhead > MAX_TOTAL_PROMPT_CHARS:
        available_user_chars = max(0, MAX_TOTAL_PROMPT_CHARS - len(header) - 2)
        user_block = user_block[:available_user_chars]
        fixed_overhead = len(header) + len(user_block) + 2
    remaining = max(0, MAX_TOTAL_PROMPT_CHARS - fixed_overhead)
    static_budget = min(len(static_context or ""), remaining // 2)
    memory_budget = min(len(memory_context or ""), remaining - static_budget)
    static_used = _truncate_segment(static_context, static_budget)
    memory_used = _truncate_segment(memory_context, memory_budget)
    prompt = f"{header}{static_used}\n{memory_used}\n{user_block}"
    if len(prompt) > MAX_TOTAL_PROMPT_CHARS:
        overflow = len(prompt) - MAX_TOTAL_PROMPT_CHARS
        memory_used = memory_used[:max(0, len(memory_used) - overflow)]
        prompt = f"{header}{static_used}\n{memory_used}\n{user_block}"
    return prompt, {"total_chars": len(prompt), "budget_chars": MAX_TOTAL_PROMPT_CHARS, "static_truncated": len(static_used) < len(static_context or ""), "memory_truncated": len(memory_used) < len(memory_context or "")}


def redact_memory_text(text):
    """Remove common credential material before explicit memory persistence."""
    text = str(text or "")
    text = re.sub(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", "[REDACTED PRIVATE KEY]", text, flags=re.DOTALL)
    patterns = [
        (r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", "Bearer [REDACTED]"),
        (r"(?i)\b(?:api[_ -]?key|access[_ -]?token|secret|password)\s*[:=]\s*[^\s,;]+", "[REDACTED CREDENTIAL]"),
        (r"\b(?:sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9]{12,}|github_pat_[A-Za-z0-9_]{12,})\b", "[REDACTED TOKEN]"),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": MODEL_NAME, "ollama_url": OLLAMA_URL, "memory_backend": MEMORY_BACKEND})


def should_persist_memory(prompt):
    normalized = " ".join(prompt.lower().split())
    memory_triggers = ("remember that", "remember this", "remember:", "save this", "save that", "save to memory", "store this", "store that", "keep this in memory", "keep in mind", "make a note that", "memorize this")
    return any(trigger in normalized for trigger in memory_triggers)


def _persist_memory(prompt, ai_response):
    safe_prompt = redact_memory_text(prompt)
    safe_response = redact_memory_text(ai_response)
    collection.add(documents=[f"User asked: {safe_prompt}\nAI replied: {safe_response}"], metadatas=[{"timestamp": "explicit_user_memory"}], ids=[f"mem_{uuid.uuid4()}"])


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
        return jsonify({"error": f"prompt exceeds maximum length of {MAX_PROMPT_CHARS} characters."}), 413
    if len(static_context) > MAX_CONTEXT_CHARS:
        return jsonify({"error": f"context exceeds maximum length of {MAX_CONTEXT_CHARS} characters."}), 413
    if not is_loopback_ollama_url(OLLAMA_URL):
        return jsonify({"error": "Ollama URL must point to a local loopback address."}), 503
    memory_context = retrieve_context(user_prompt)
    full_prompt, _budget = build_context(static_context, memory_context, user_prompt)
    selected_model = MODEL_NAME
    try:
        try:
            payload_response = _model_request(OLLAMA_URL, selected_model, full_prompt)
        except requests.exceptions.HTTPError as exc:
            if not _is_model_not_found(exc):
                raise
            available = discover_local_models(OLLAMA_BASE_URL)
            selected_model = select_local_model(MODEL_NAME, available)
            if selected_model is None:
                return jsonify({"error": "Configured local model is unavailable and no fallback model was found."}), 503
            payload_response = _model_request(OLLAMA_URL, selected_model, full_prompt)
        ai_response = payload_response.get("response") if isinstance(payload_response, dict) else None
        if not isinstance(ai_response, str):
            return jsonify({"error": "Ollama returned no valid 'response' field."}), 502
        ai_response = ai_response[:MAX_RESPONSE_CHARS]
    except requests.exceptions.RequestException as exc:
        return jsonify({"error": f"Local LLM request failed: {exc}"}), 502
    except (ValueError, TypeError) as exc:
        return jsonify({"error": f"Invalid response from local LLM: {exc}"}), 502
    if should_persist_memory(user_prompt):
        try:
            _persist_memory(user_prompt, ai_response)
        except Exception as exc:
            print(f"Warning: failed to save memory: {exc}")
    return jsonify({"response": ai_response})


if __name__ == "__main__":
    print("PROJECT-NAS Memory Injector running on port 5000...")
    app.run(host="127.0.0.1", port=5000)
