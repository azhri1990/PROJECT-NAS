# PROJECT-NAS Autopilot Checkpoint

**Checkpoint date:** 2026-08-15
**Active branch:** `feat/omni-device-ai-bridges-v1`
**Pull request:** #5 — `feat: add Omni mobile AI provider bridges`

## User constraints

- Continue building without repeatedly asking whether to proceed.
- Keep additional spend at **$0** by default.
- Prefer local/open-source tools and existing hardware.
- When an interface reaches a token/credit/usage/capability limit, switch to another compatible interface instead of spending money.
- If no safe compatible interface exists, persist the state in GitHub and resume later.
- Preserve the original PROJECT-NAS architecture; integrations must remain replaceable adapters.
- Security is non-negotiable: least privilege, explicit capabilities, allowlists, secret isolation, auditability, sandboxing, and verification.

## Current architecture

PROJECT-NAS remains the orchestration, policy, memory, and audit boundary.

Current Omni bridge candidates:

- Ollama Local AI — verified OpenAI-compatible local endpoint path.
- Hermes Agent Android — device/agent surface; do not assume the Android app itself is an API server.
- Hermes-Relay — operator/relay surface; not a trusted model backend.
- Codex/Codex Mobile — coding/operator surface; no unverified execution contract assumed.
- PocketPal — optional offline inference; no network API assumed.
- OfflineGPT — optional offline inference; no network API assumed.
- OpenClaw Node — candidate Android companion/device boundary.
- Termux — Android Linux execution substrate; must remain capability-gated.
- Vicoa — candidate mobile operator surface for coding agents.

## Verified CI checkpoint

The previous failing Omni CI run was corrected. The latest workflow completed all listed steps successfully: dependency installation, Python compilation, full test suite, PROJECT-NAS doctor diagnostics, and progress reporter.

## Last persisted implementation commit

`86cab8e67b5f2894fc6f8c575caa0aaf86843ddb`

This commit persists the $0/autopilot continuation policy in `ACTION-PLAN.md`.

## Next engineering action

1. Run/verify the CI triggered by the checkpoint commit.
2. Add end-to-end `/chat` coverage using a fake local Ollama endpoint and isolated Chroma storage.
3. Add deterministic local-first fallback routing with paid providers disabled by default.
4. Add capability negotiation, authentication, approval policy, sandboxing, and audit logging before any Hermes/OpenClaw/Termux device execution.
5. Re-run full verification after each milestone.

## Resume rule

Do not restart completed work. Read `ACTION-PLAN.md`, this checkpoint, the active PR, and the latest CI result. Continue from the first incomplete engineering action and preserve all verified security constraints.
