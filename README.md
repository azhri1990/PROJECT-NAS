# PROJECT-NAS

PROJECT-NAS is a local-first personal operating system runtime designed to run across PC and mobile environments without requiring paid cloud AI subscriptions.

## Design principles

1. **Local first** — local models and local services are preferred.
2. **Bounded by default** — prompts, memory, tools, timeouts, and repository reads have explicit limits.
3. **Deny by default** — process execution, network access, and repository writes require an explicit policy path.
4. **Reproducible** — runtime behavior must be executable, tested, documented, and reproducible on a clean environment.
5. **Portable** — configuration is environment-driven so PC and Termux/mobile runtimes can share the same contracts.
6. **Observable** — health, progress, diagnostics, and controller ownership are explicit runtime surfaces.

## Runtime layers

```text
PROJECT-NAS
├── Core contracts and configuration
├── Runtime controller
│   ├── Ollama
│   └── memory/chat service
├── Control plane
│   ├── status.health
│   ├── status.progress
│   ├── prompt.get
│   └── memory.read
├── Policy engine
├── Memory layer
├── Local model layer
└── Tests + CI + diagnostics
```

## Installation

Create the virtual environment and install the canonical developer dependency set:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` is the single developer entrypoint and includes the runtime and test requirement files. CI installs those split files directly so runtime-only and test-only environments remain independently reproducible.

For a minimal mobile/Termux runtime environment, use:

```bash
pip install -r requirements-runtime-mobile.txt
```

## Local runtime

Default local services:

- Ollama: `http://127.0.0.1:11434`
- Memory API: `http://127.0.0.1:5000`
- Default model: `llama3.2:3b`

Start the runtime:

```bash
runtime/project-nas.sh start
```

Check it:

```bash
runtime/project-nas.sh status
runtime/project-nas.sh doctor
```

Stop only services owned by the controller:

```bash
runtime/project-nas.sh stop
```

Interactive local chat:

```bash
runtime/project-nas.sh chat
```

## Control plane

The FastAPI backend exposes a bounded, read-only tool gateway:

| Tool | Purpose |
|---|---|
| `status.health` | Aggregate runtime health without exposing memory contents |
| `status.progress` | Bounded repository progress |
| `prompt.get` | Bounded canonical prompt retrieval |
| `memory.read` | Bounded memory retrieval |

HTTP surfaces are:

- `GET /health` — aggregate runtime health;
- `GET /prompt` — bounded canonical prompt;
- `GET /progress?commits=N` — bounded repository progress;
- `POST /tools/{tool_name}` — policy-gated control-plane execution.

The policy engine denies process execution, arbitrary network access, and repository writes by default.

## Chat, model fallback, and memory governance

`/chat` uses the configured local model first. If Ollama reports that model is unavailable, PROJECT-NAS discovers models from the **local loopback** Ollama `/api/tags` endpoint and selects a deterministic fallback. No remote model endpoint is permitted.

Chat input, static context, retrieved memory, and model responses have explicit size limits. A deterministic total prompt budget reserves the system/runtime contract and user request before allocating remaining space between static context and retrieved memory.

Memory persistence is opt-in: ordinary chat is not stored. Explicit memory requests are redacted for common API keys, bearer tokens, passwords, and private-key material before persistence. SQLite retention is bounded by `PROJECT_NAS_MAX_PERSISTED_MEMORIES`; read APIs remain independently bounded.

## Testing

Run the complete suite:

```bash
python -m pytest -q
```

Additional local verification:

```bash
bash -n runtime/project-nas.sh
python -m compileall -q runtime tests
git diff --check
python runtime/doctor.py
python runtime/progress.py --commits 5
```

CI performs the same core checks in a Python 3.12 container, installs Git for repository inspection, and fails on doctor errors rather than silently continuing.

## Configuration

Important environment variables include:

- `PROJECT_NAS_OLLAMA_BASE_URL`
- `PROJECT_NAS_OLLAMA_URL`
- `PROJECT_NAS_OLLAMA_MODEL`
- `PROJECT_NAS_OLLAMA_TIMEOUT`
- `PROJECT_NAS_MEMORY_DB`
- `PROJECT_NAS_MEMORY_HEALTH_URL`
- `PROJECT_NAS_SESSION_DB`
- `PROJECT_NAS_MAX_PROMPT_CHARS`
- `PROJECT_NAS_MAX_CONTEXT_CHARS`
- `PROJECT_NAS_MAX_RESPONSE_CHARS`
- `PROJECT_NAS_MAX_TOTAL_PROMPT_CHARS`
- `PROJECT_NAS_MAX_PERSISTED_MEMORIES`

## Remaining roadmap gates

Before autonomous plugins, remote-device control, or unrestricted process execution are enabled, PROJECT-NAS still requires:

- repository-wide security review;
- explicit approval and verification gates for every write/process/network capability;
- dedicated integration tests for any future privileged capability.

These are future capability gates, not assumptions that those capabilities already exist.
