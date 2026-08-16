PROJECT-NAS — Runtime Action Plan

Goal
----
Maintain a reproducible, local-first runtime whose documented state matches the code and whose core behavior is continuously tested.

Current baseline
----------------
1. `runtime/progress.py` — repository progress reporter.
2. `runtime/progress.ps1` — Windows PowerShell fallback.
3. `runtime/prompt_loader.py` — canonical prompt loader, independent of cwd.
4. `runtime/backend.py` — FastAPI local backend with prompt, progress, todos, validated custom-plugin endpoints, and policy-gated tool execution.
5. `runtime/tool_gateway.py` — typed tool registry, deterministic policy gate, bounded input, timeout, JSON result validation, and bounded audit events.
6. `runtime/policy.py` — capability and risk primitives with deny-by-default write/process/network policy.
7. `runtime/memory_injector.py` — Flask bridge to Chroma + local Ollama.
8. `requirements-runtime.txt` — explicit FastAPI/Uvicorn/Flask/Requests/Chroma runtime dependencies.
9. `tests/` — regression coverage for backend, policy, tool gateway, progress, prompt loader, and LLM configuration.
10. `.github/workflows/progress-check.yml` — compiles runtime/test Python and executes the full test suite.

Verified fixes
--------------
- Removed the machine-specific Copilot session DB path from the backend.
- Added environment-configurable session and memory paths.
- Added plugin-name validation against path traversal.
- Corrected the memory bridge default model to the documented local `llama3.2:3b`.
- Added configurable Ollama URL/model settings.
- Added missing memory-runtime dependencies to CI/runtime requirements.
- Removed the arbitrary ten-word minimum from `/chat`; transport now accepts valid prompts and lets the model decide whether more context is needed.
- Made prompt loading independent of the caller's working directory.
- Made the shell wrapper locate the repository from its own script path.
- Hardened shell HTTP failure handling and timeouts.
- Hardened progress reporter timestamp generation and argument validation.
- Updated JARVIS documentation so it distinguishes implemented components from roadmap items.
- Added the first Omni Core policy boundary: process/network/write capabilities are denied by default and read-only tools require explicit typed registration.
- Added bounded `repo.progress` tool execution with input validation, timeout handling, JSON result validation, and audit events.

Next engineering gate
---------------------
1. Confirm the complete CI suite for the Omni policy/tool gateway branch.
2. Add end-to-end tests for `/chat` with a fake local Ollama endpoint and isolated Chroma storage.
3. Add model discovery/health checks and deterministic fallback routing.
4. Add context-budgeting/compression before large MASTER_PROMPT + memory payloads reach the model.
5. Add explicit memory retention/redaction policy before expanding automatic memory writes.
6. Perform a repository-wide security review before exposing plugins or remote device access.
7. Keep autonomous write/process/network capabilities behind explicit approval and verification gates.

Principle
---------
A feature is not considered complete because a file exists. It is complete only when its behavior is executable, tested, documented accurately, and reproducible on a clean environment.
