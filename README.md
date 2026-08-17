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

The FastAPI backend exposes a bounded tool gateway. The default gateway is intentionally read-only:

| Tool | Purpose |
|---|---|
| `status.health` | Aggregate runtime health without exposing memory contents |
| `status.progress` | Bounded repository progress |
| `prompt.get` | Bounded canonical prompt retrieval |
| `memory.read` | Bounded memory retrieval |

The policy engine denies process execution, arbitrary network access, and repository writes by default.

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
```

CI performs the same core checks and fails on doctor errors rather than silently continuing.

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

## Roadmap gates

Before autonomous plugins, remote-device control, or unrestricted process execution are enabled, PROJECT-NAS must have:

- end-to-end `/chat` tests with an isolated fake local model endpoint;
- deterministic model discovery and fallback routing;
- context budgeting/compression;
- explicit memory retention and redaction policy;
- repository-wide security review;
- approval and verification gates for every write/process/network capability.

These are engineering gates, not assumptions that the capability already exists.
