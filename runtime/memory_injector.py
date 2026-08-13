import os
import uuid
import chromadb
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Anchor the DB to this script's folder, not the current working directory.
# Running this from cron/systemd with a different cwd used to silently
# create a new empty DB.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "claude-mem-db")

client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(name="project_nas_memory")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma4"


def retrieve_context(query_text):
    """Search the vector DB for relevant past memories."""
    try:
        results = collection.query(query_texts=[query_text], n_results=3)
    except Exception as e:
        print(f"Warning: memory retrieval failed: {e}")
        return ""
    if results and results.get('documents') and results['documents'][0]:
        return (
            "\n--- INJECTED MEMORY ---\n"
            + "\n".join(results['documents'][0])
            + "\n--- END MEMORY ---\n"
        )
    return ""


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    user_prompt = data.get('prompt')
    if not user_prompt or not isinstance(user_prompt, str) or not user_prompt.strip():
        return jsonify({"error": "Missing 'prompt' field."}), 400

    # Background context (e.g. CLAUDE.md) is kept separate from the question,
    # so the clarifying-question check and the memory search both look at
    # what the user actually asked, not a huge pasted file.
    static_context = data.get('context', '') or ''

    if len(user_prompt.split()) < 10:
        return jsonify({
            "response": "I need more context, brother. Tell me exactly what "
                         "you're working on in PROJECT-NAS today, and what your goal is."
        })

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
        ai_response = response.json().get('response')
        if ai_response is None:
            return jsonify({
                "response": "Ollama responded but sent no 'response' field. "
                             "Check the model name and Ollama version."
            })
    except requests.exceptions.RequestException as e:
        # Only real connection/HTTP problems get labeled as a connection error.
        return jsonify({"response": f"Error connecting to local LLM: {e}. Is Ollama running?"})

    # Memory write is separate from the LLM call. A save failure no longer
    # gets mislabeled as "can't connect to Ollama," and no longer overwrites
    # existing memories via colliding IDs.
    try:
        collection.add(
            documents=[f"User asked: {user_prompt}\nAI replied: {ai_response}"],
            metadatas=[{"timestamp": "session_auto"}],
            ids=[f"mem_{uuid.uuid4()}"]
        )
    except Exception as e:
        print(f"Warning: failed to save memory: {e}")

    return jsonify({"response": ai_response})


if __name__ == '__main__':
    print("PROJECT-NAS Memory Injector running on port 5000...")
    app.run(port=5000)
