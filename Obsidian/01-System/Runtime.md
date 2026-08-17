# Runtime

## Implemented components

| Component | Purpose |
|---|---|
| `runtime/backend.py` | FastAPI local API: health, prompt, progress, todos, controlled tools |
| `runtime/memory_injector.py` | Flask bridge to memory storage and local Ollama chat |
| `runtime/prompt_loader.py` | Canonical prompt loading independent of working directory |
| `runtime/progress.py` | Repository progress reporting |
| `runtime/project-nas.sh` | Repository-rooted runtime controller and chat wrapper |
| `runtime/tool_gateway.py` | Bounded control-plane tool registry and execution gate |
| `runtime/policy.py` | Deny-by-default capability policy |
| `requirements-runtime.txt` | Runtime dependency manifest |
| `tests/` | Regression and contract coverage |
| `.github/workflows/progress-check.yml` | Reproducible Ubuntu verification CI |

## Control-plane tools

- `status.health` — aggregate health without memory contents.
- `status.progress` — bounded repository progress.
- `prompt.get` — bounded canonical prompt retrieval.
- `memory.read` — bounded memory retrieval.

Process execution, arbitrary network access, and repository writes remain denied by default.

## Local AI

- Ollama is the default local model provider.
- Default documented model: `llama3.2:3b`.
- The configured model is preferred; if Ollama reports it missing, local model discovery selects a deterministic fallback.
- Ollama endpoints are loopback-only by default and remote model endpoints are rejected.
- Memory uses persistent Chroma when available and SQLite as the mobile-friendly fallback.
- Ollama URL/model, memory paths, prompt budgets, and retention limits are configurable through environment variables.

## Governance

- Chat persistence is explicit-trigger only; ordinary chat is not stored.
- Explicit memory writes redact common API keys, bearer tokens, passwords, and private-key material.
- SQLite persistence is bounded by `PROJECT_NAS_MAX_PERSISTED_MEMORIES`.
- Prompt construction has independent input limits plus a deterministic total context budget.
- Controller stop operations require exact PID and process-command identity ownership.
- Controller readiness probes use the memory `/health` endpoint rather than a POST-only `/chat` endpoint.

## Verification

Required local checks:

```bash
bash -n runtime/project-nas.sh
python -m compileall -q runtime tests
python -m pytest -q tests
python runtime/doctor.py
python runtime/progress.py --commits 5
git diff --check
```

CI runs the same verification on Ubuntu 24.04 using an isolated Python environment.

## Remaining runtime gates

- Repository-wide security review before remote/plugin/device exposure.
- Explicit approval and verification gates before adding write/process/network capabilities.
- Dedicated integration coverage for any future privileged capability.
