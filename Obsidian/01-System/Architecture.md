# PROJECT-NAS Architecture

## Objective

PROJECT-NAS is designed as a privacy-first, local-first assistant that can manage projects, surface context, run automation, and act as a strategic AI advisor across PC, mobile, and tablet.

## Current architecture

```text
Obsidian Knowledge Layer
        ↓
FastAPI Local Backend
        ↓
Local orchestration / prompts / state
        ↓
Flask LLM + Memory Bridge
   ↙                 ↘
Ollama             Chroma
(local model)     (vector memory)
        ↓
SQLite application/session state
```

## Planned layers

- Desktop: Electron
- Mobile/tablet: responsive PWA
- Voice: local/browser STT + TTS
- Integrations: GitHub, calendar, files and other connectors
- Security: threat-model-driven plugin controls and encrypted sync where explicitly enabled

## Boundaries

**Implemented:** FastAPI backend, local LLM/memory bridge, prompt loading, progress reporting, runtime dependencies, regression tests and CI.

**Planned:** full frontend, voice layer, orchestration upgrades, device access and broader integrations.

See [[02-AI/JARVIS-Roadmap]] for capability status.
