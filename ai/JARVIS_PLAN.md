PROJECT-NAS: JARVIS-Like Assistant — Current Architecture & Roadmap

Objective
---------
Turn PROJECT-NAS into a cross-platform, privacy-first, local-first assistant for PC, mobile, and tablet that manages projects, surfaces context, runs automation, and acts as a strategic AI advisor.

Current implemented runtime
---------------------------
- FastAPI backend: `runtime/backend.py`
  - `/` service health
  - `/prompt` canonical prompt retrieval
  - `/progress` repository state
  - `/todos` CRUD persistence
  - `/custom/{plugin_name}` trusted local plugin execution with filename validation
- Local LLM/memory bridge: `runtime/memory_injector.py`
  - Flask `/health` and `/chat`
  - Chroma persistent memory
  - Ollama local generation
  - configurable via `PROJECT_NAS_MEMORY_DB`, `PROJECT_NAS_OLLAMA_URL`, and `PROJECT_NAS_OLLAMA_MODEL`
  - default model: `llama3.2:3b`
- Prompt loader: `runtime/prompt_loader.py`, independent of current working directory.
- Progress reporter: `runtime/progress.py`.
- Shell wrapper: `runtime/project-nas.sh`, rooted to the repository rather than the caller's working directory.
- Runtime dependency manifest: `requirements-runtime.txt`.
- CI: `.github/workflows/progress-check.yml` runs compilation and the complete test suite.
- Tests cover backend, progress, prompt loading, and local LLM configuration.

Architecture
------------
Backend: FastAPI local API for system state, prompts, progress, todos, and controlled extensions.
LLM bridge: Flask service to local Ollama + Chroma memory.
Persistence: SQLite for application/session todos and Chroma for vector memory.
Frontend: not yet implemented in this repository; planned Electron desktop + responsive PWA.
Voice: not yet implemented; planned local/browser STT/TTS.
Cloud providers: optional future integrations only; local execution remains the default.

Security/privacy baseline
-------------------------
- No machine-specific absolute session DB path in source.
- Local runtime state is ignored by Git.
- Plugin route rejects non-identifier names to prevent path traversal.
- Cloud LLM use is not required for the current runtime.
- Secrets files and common private-key formats are excluded by `.gitignore`.

Roadmap
-------
Phase 0 — Runtime foundation — substantially complete
- Canonical prompt loading
- Progress reporting
- FastAPI backend
- Local LLM/memory bridge
- Runtime dependencies
- Regression tests and CI

Phase 1 — Assistant MVP
- Wire FastAPI `/ask`-style orchestration directly to the local LLM bridge, or consolidate `/chat` into FastAPI.
- Add model health/discovery and fallback routing.
- Add context budgeting/compression.
- Add explicit memory write/read policies.

Phase 2 — UI and device access
- Electron desktop UI.
- Responsive PWA for mobile/tablet.
- Local voice input/output.

Phase 3 — Integrations and hardening
- GitHub, calendar, files and other connectors.
- Encrypted device sync where explicitly enabled.
- Security scanning and threat-model-driven plugin controls.

Important
---------
The roadmap is not a claim that future capabilities already exist. The repository's source and passing CI are the authoritative implementation state.
