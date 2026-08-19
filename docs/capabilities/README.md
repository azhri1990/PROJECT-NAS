# PROJECT-NAS Capability Registry

The capability registry classifies installed apps without treating installation as authorization.

## Files

- `app-capability-matrix.json` — canonical reviewed capability records.
- `device-role-matrix.md` — Android/tablet/PC/GitHub/NAS role mapping.
- `PROJECT-NAS-APP-ECOSYSTEM.md` — system-level architecture and operating rules.

## Classifications

- `CORE` — directly useful to build or operate PROJECT-NAS/BOB.
- `WORKER` — optional AI/agent/model worker delegated bounded tasks.
- `TOOL` — bounded utility such as design, documentation, media, or diagnostics.
- `BACKUP` — resilience/fallback capability.
- `PERSONAL` — outside the engineering system.
- `IGNORE` — duplicate, low-value, unverified, or out of scope.

## Important rule

**Installed does not mean authorized.** The registry cannot grant permissions. PROJECT-NAS PolicyEngine and ToolGateway remain the execution authority.

## Core stack

The intended minimum engineering stack is GitHub + Codex + Termux + local Ollama, with PROJECT-BOB coordinating governed work across Android/tablet/PC. External AI apps remain replaceable workers.
