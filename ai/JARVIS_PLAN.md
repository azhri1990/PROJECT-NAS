PROJECT-NAS: JARVIS-Like Assistant — Overview & Roadmap

Objective
---------
Turn PROJECT-NAS into a cross-platform, privacy-first, "Jarvis-like" assistant available on PC, mobile, and tablet that helps manage projects, surface context, run automation, and act as a strategic AI advisor using the existing MASTER_PROMPT and consolidated profile resources.

Core capabilities (MVP)
-----------------------
- Local-first backend that can run on user machines (desktop/laptop) and optionally on a small server.
- Persistent session memory and todos (already present as a session SQLite DB) accessible through a local API.
- Prompt loader that supplies the canonical MASTER_PROMPT / AI operating system to any local agent or automation.
- Cross-platform UI: Electron-based desktop app plus a Progressive Web App (PWA) for mobile/tablet.
- Short prompt command system (slash-commands) supported by UI shortcuts and templates (e.g., /firstdraft, /qa, /handoff).
- Actionables: export/import of session state, attach artifacts to PRs, and run repository checks (progress reporter exists).
- Voice input/output (STT/TTS) for conversational interactions.

Architecture (high level)
-------------------------
- Backend: FastAPI (Python) or lightweight local process that exposes:
  - /progress (returns runtime/progress output)
  - /prompt (returns canonical MASTER_PROMPT)
  - /todos (CRUD for session todos; proxies the session SQLite DB)
  - /ask (accepts user prompt, runs against LLM bridge or local model)
- Frontend:
  - Electron app (desktop) wrapping a React/Preact UI that talks to backend on localhost.
  - PWA deployed from repo for mobile/tablet; same UI codebase used with responsive design.
- Optional bridge to cloud LLMs with configurable provider keys (user opt-in). Local-first by default.
- Persistence: session SQLite DB (existing), plus optional encrypted sync to user cloud storage.
- Extensions: plugin system to add connectors (GitHub, calendar, Slack, file stores).

Privacy & Safety
----------------
- Default to local-only execution and storage.
- Any cloud LLM or sync is opt-in and requires explicit user configuration.
- Mask or redact sensitive profile fields before saving in repo files (ai/PROFILE.md is redacted).

Phased roadmap (recommended)
-----------------------------
Phase 0 — Tidy & bootstrap (1-2 days)
- Import authoritative ai/MASTER_PROMPT.md and ai/PROFILE.md (redacted) into repo.
- Add runtime/prompt_loader.py (to load prompt into automation).
- Add ACTION-PLAN.md and JARVIS_PLAN.md (done/added).

Phase 1 — MVP local assistant (2-4 weeks)
- Implement backend (FastAPI) with endpoints: /prompt, /progress, /todos, /ask (bridge to LLM or mock).
- Build Electron UI that shows progress reporter, todos editor, and an "Ask Jarvis" chat view supporting slash-commands.
- Wire prompt_loader into /ask so the assistant uses canonical MASTER_PROMPT.
- Add basic STT/TTS support via browser APIs or native modules.

Phase 2 — Tests, CI, and packaging (1-2 weeks)
- Add tests for runtime/progress.py and prompt_loader.
- Create CI workflow to run checks and tests.
- Package Electron app for Windows/macOS/Linux and prepare PWA deployment.

Phase 3 — Integrations & polish (ongoing)
- Add GitHub integration (attach exports to PRs, create issues), calendar, file connectors.
- Encrypted sync and device pairing for cross-device continuity.
- Plugin marketplace and skilled memory feature extraction from imported documents (PDF/Word/Excel).

Actionable next steps (pick which to run now)
---------------------------------------------
1. Import AI artifacts: copy MASTER_PROMPT.md, Nash_Consolidated doc, and the PDF text into ai/ (requires PDF-to-text). (Recommended)
2. Create runtime/prompt_loader.py (small utility) — will provide a canonical prompt to the backend and tools.
3. Start backend skeleton (FastAPI) with /prompt and /progress endpoints.
4. Create Electron app skeleton and wire to backend.

Session todos created will track the work and can be progressed via the existing session DB.

