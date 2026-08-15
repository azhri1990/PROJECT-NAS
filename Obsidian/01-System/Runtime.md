# Runtime

## Implemented components

| Component | Purpose |
|---|---|
| `runtime/backend.py` | FastAPI local API: health, prompt, progress, todos, controlled extensions |
| `runtime/memory_injector.py` | Flask bridge to Chroma + local Ollama |
| `runtime/prompt_loader.py` | Canonical prompt loading independent of working directory |
| `runtime/progress.py` | Repository progress reporting |
| `runtime/project-nas.sh` | Repository-rooted shell wrapper |
| `requirements-runtime.txt` | Runtime dependency manifest |
| `tests/` | Regression coverage |
| `.github/workflows/progress-check.yml` | Compilation + test CI |

## Local AI

- Ollama is the default local model provider.
- Default documented model: `llama3.2:3b`.
- Memory uses persistent Chroma storage.
- Ollama URL/model and memory paths are configurable through environment variables.

## Hardening already performed

- Removed machine-specific session DB paths.
- Added configurable session/memory paths.
- Added plugin-name validation against path traversal.
- Corrected local model configuration.
- Added missing runtime dependencies to CI.
- Removed the arbitrary ten-word minimum from `/chat`.
- Made prompt loading independent of caller working directory.
- Hardened shell HTTP failures/timeouts.
- Hardened progress timestamp and argument handling.

## Next runtime gates

- Full CI verification after latest changes.
- End-to-end `/chat` tests using fake Ollama + isolated Chroma.
- Model health/discovery + deterministic fallback routing.
- Context budgeting/compression.
- Explicit memory retention/redaction policy.
- Repository-wide security review before remote/plugin/device exposure.
