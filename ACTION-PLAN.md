PROJECT-NAS — Runtime Action Plan

Goal
----
Maintain a reproducible, local-first runtime whose documented state matches the code and whose core behavior is continuously tested.

Current baseline
----------------
1. `runtime/progress.py` — repository progress reporter.
2. `runtime/progress.ps1` — Windows PowerShell fallback.
3. `runtime/prompt_loader.py` — canonical prompt loader, independent of cwd.
4. `runtime/backend.py` — FastAPI local backend with prompt, progress, todos, validated custom-plugin endpoints, and Omni provider discovery/health endpoints.
5. `runtime/memory_injector.py` — Flask bridge to Chroma + local Ollama.
6. `runtime/omni/` — provider-agnostic Omni bridge layer with typed provider contracts, OpenAI-compatible HTTP adapter, mobile AI catalog, environment-driven configuration, and network/security controls.
7. `requirements-runtime.txt` — explicit FastAPI/Uvicorn/Flask/Requests/Chroma runtime dependencies.
8. `tests/` and `runtime/tests/` — regression and Omni bridge coverage.
9. `.github/workflows/progress-check.yml` — compiles runtime/test Python and executes both test trees.
10. `docs/OMNI-DEVICE-BRIDGES.md` — verified integration boundaries for Ollama Local AI, Hermes Agent, Hermes-Relay, Codex Mobile, PocketPal AI, and OfflineGPT.

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
- Added local-first Omni provider contracts and health discovery without exposing provider secrets.
- Added deterministic profiles for the six mobile AI integrations and disabled unsupported/unverified adapters by default.
- Added an explicit network allowlist for non-loopback provider endpoints.

Next engineering gate
---------------------
1. Run the complete CI suite on the Omni bridge branch and fix any regressions.
2. Add end-to-end tests for `/chat` with a fake local Ollama endpoint and isolated Chroma storage.
3. Add policy/capability negotiation before delegating Hermes terminal, filesystem, notification, media, or device-control actions.
4. Add model discovery and deterministic fallback routing behind the Omni provider registry.
5. Add context-budgeting/compression before large MASTER_PROMPT + memory payloads reach a model.
6. Add explicit memory retention/redaction policy before expanding automatic memory writes.
7. Add verified Codex Mobile, PocketPal, and OfflineGPT adapters only when stable machine-readable APIs are available.
8. Perform a repository-wide security review before exposing remote device control.

Principle
---------
A feature is not considered complete because a file exists. It is complete only when its behavior is executable, tested, documented accurately, and reproducible on a clean environment.
