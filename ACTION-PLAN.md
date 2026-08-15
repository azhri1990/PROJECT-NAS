PROJECT-NAS — Runtime Action Plan

Goal
----
Maintain a reproducible, local-first runtime whose documented state matches the code and whose core behavior is continuously tested.

Operating constraints
---------------------
1. **$0 additional spend is the default.** Local/open-source runtimes and existing hardware are preferred.
2. Paid cloud providers, paid APIs, and metered fallbacks stay disabled unless explicitly authorized.
3. If a selected tool/interface reaches a usage, credit, token, or capability limit, route to the next compatible local/available interface instead of silently spending money.
4. If no safe fallback exists, stop the active implementation step, persist the current state, test results, decisions, and exact next action in GitHub, then resume from that checkpoint later.
5. PROJECT-NAS remains the orchestration, policy, memory, and audit boundary. External agents and mobile apps are capability providers, not trusted authorities.
6. Never expose unrestricted shell, filesystem, device-control, GitHub, or credential access to model output.
7. Never claim a feature is complete without executable verification.

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
10. `docs/OMNI-DEVICE-BRIDGES.md` — verified integration boundaries for Ollama Local AI, Hermes Agent - Android, Hermes-Relay, Codex Mobile, PocketPal AI, and OfflineGPT.

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
- Added a generic OpenAI-compatible adapter for a separately operated verified server endpoint.
- Added an explicit network allowlist for non-loopback provider endpoints.
- Added `runtime/__init__.py` so the new runtime package is importable by CI tests.

Next engineering gates
----------------------
1. Complete and pass the full CI suite on the Omni bridge branch.
2. Add end-to-end `/chat` tests using a fake local Ollama endpoint and isolated Chroma storage.
3. Add deterministic local-first fallback routing behind the Omni provider registry, with paid providers disabled by default.
4. Add capability negotiation, authentication, approval policy, sandboxing, and audit logging before delegating Hermes/OpenClaw/Termux terminal, filesystem, notification, media, or device-control actions.
5. Add model discovery and health-aware routing without automatic paid fallback.
6. Add context-budgeting/compression before large MASTER_PROMPT + memory payloads reach a model.
7. Add explicit memory retention/redaction policy before expanding automatic memory writes.
8. Add verified Codex Mobile, PocketPal, and OfflineGPT adapters only when stable machine-readable APIs are available.
9. Perform a repository-wide security review before exposing remote device control.
10. Keep a machine-readable/persistent checkpoint in GitHub whenever work pauses, hits a tool limit, or requires a different interface.

Continuation protocol
---------------------
When continuing work, inspect this file and the current Git/CI state first. Resume from the first incomplete engineering gate; do not restart completed work. For every completed gate, record the verification evidence in the relevant PR/commit documentation. If an interface becomes unavailable, use the next compatible interface while preserving the same repository state and tests.

Principle
---------
A feature is not considered complete because a file exists. It is complete only when its behavior is executable, tested, documented accurately, and reproducible on a clean environment.
