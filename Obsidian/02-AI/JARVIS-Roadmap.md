# JARVIS Roadmap

## Target

A cross-platform, privacy-first assistant for PC, mobile and tablet with project management, context retrieval, automation and strategic reasoning.

## Status

### Phase 0 — Runtime foundation
**Substantially complete**

- Canonical prompt loading
- Progress reporting
- FastAPI backend
- Local Ollama + Chroma bridge
- Runtime dependencies
- Regression tests and CI

### Phase 1 — Assistant MVP
**Next**

- Unified `/ask` orchestration
- Model health/discovery
- Deterministic fallback routing
- Context budgeting/compression
- Explicit memory read/write policies

### Phase 2 — Device experience

- Electron desktop UI
- Responsive PWA
- Local/browser voice input and output

### Phase 3 — Integrations and hardening

- GitHub, calendar, files and other connectors
- Explicitly enabled encrypted device sync
- Security scanning and threat-model-driven plugin controls

> Roadmap items are not implementation claims. Repository source + passing CI define actual capability.

Source: `ai/JARVIS_PLAN.md`
