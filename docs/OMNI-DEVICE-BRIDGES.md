# PROJECT-NAS Omni Device AI Bridges

This document records the verified integration boundary for the six Android/mobile AI applications currently being evaluated for PROJECT-NAS.

## Architecture rule

PROJECT-NAS remains the orchestrator, policy owner, memory owner, and audit boundary. Mobile applications are capability providers or operator surfaces. They do not receive unrestricted PROJECT-NAS authority.

The first bridge uses the OpenAI-compatible HTTP contract because it is already supported by both Ollama Local AI and Hermes Agent. PROJECT-NAS never assumes an app is compatible merely because its name suggests an AI API.

## Integration matrix

| App | Role in PROJECT-NAS | v1 status | Integration boundary |
| --- | --- | --- | --- |
| Ollama Local AI | Android/local model gateway | Supported | OpenAI-compatible `/v1` endpoint; explicit URL required |
| Hermes Agent - Android | Android agent/device runtime | Supported as model endpoint | OpenAI-compatible Hermes API server; explicit URL/key configuration required |
| Hermes-Relay | Android client/relay surface | Optional | Talks to a configured Hermes instance; not a model provider |
| Codex Mobile | Browser/app-server coding surface | Optional | Operator surface; no direct PROJECT-NAS execution contract assumed |
| PocketPal AI | On-device local inference | Unverified | No remote PROJECT-NAS API is assumed |
| OfflineGPT | On-device offline inference | Unverified | No remote PROJECT-NAS API is assumed |

## Environment configuration

Only explicitly configured endpoints are enabled.

```text
PROJECT_NAS_OMNI_OLLAMA_URL=http://192.168.1.20:11434/v1
PROJECT_NAS_OMNI_OLLAMA_MODEL=qwen3
PROJECT_NAS_OMNI_OLLAMA_API_KEY_ENV=

PROJECT_NAS_OMNI_HERMES_URL=http://192.168.1.30:8642/v1
PROJECT_NAS_OMNI_HERMES_MODEL=hermes-agent
PROJECT_NAS_OMNI_HERMES_API_KEY_ENV=HERMES_API_SERVER_KEY

PROJECT_NAS_OMNI_ALLOWED_HOSTS=192.168.1.20,192.168.1.30
```

Do not place the API key itself in these settings. `*_API_KEY_ENV` contains the name of an environment variable whose value is read only at request time.

Loopback endpoints are permitted for local development. LAN or public hosts must be explicitly allowlisted.

## Hermes Agent boundary

Hermes Agent's API server exposes an OpenAI-compatible endpoint. The default documented server bind is loopback and the API server uses a bearer key when network access is enabled. PROJECT-NAS therefore treats Hermes as an untrusted agent peer and does not inherit Hermes terminal/file permissions automatically.

The next security milestone must add explicit capability negotiation before PROJECT-NAS can delegate terminal, filesystem, notification, media, or device-control actions.

## Hermes-Relay boundary

Hermes-Relay is an Android client for a user-operated Hermes instance. It can optionally pair with a relay service for additional power tools. PROJECT-NAS treats the relay as an operator/device surface, not as a trusted model backend.

## Codex Mobile boundary

Codex Mobile is a browser-accessible bridge around a Codex app-server workflow and can run on Windows or Termux/Android. It is useful as a mobile operator surface for coding sessions, but PROJECT-NAS does not yet assume a stable machine-readable task API from it. The safe v1 position is to keep it outside the execution trust boundary.

## PocketPal and OfflineGPT

Both are useful local/offline inference options, but PROJECT-NAS does not assume a network API for either application. They remain optional future adapters until a documented, testable endpoint is available.

## Security requirements

- Default deny for arbitrary provider URLs.
- Loopback allowed for local development; non-loopback hosts require an explicit allowlist.
- Credentials are never stored in provider configuration values.
- Provider health responses never include authorization headers or secret values.
- Chat input is bounded by `max_input_chars`.
- HTTP calls have explicit timeouts.
- Provider failures do not trigger silent paid-provider fallback.
- Device-control and terminal operations are not exposed by the v1 bridge.

## Upgrade path

This layer is deliberately an adapter, not a hard-coded architecture. Future milestones can add:

1. Hermes capability discovery (`/v1/capabilities`, `/v1/toolsets`, `/v1/skills`).
2. Explicit PROJECT-NAS policy checks before delegated tool execution.
3. Codex task delegation through a stable app-server contract if one is selected and verified.
4. A PocketPal adapter if a stable OpenAI-compatible endpoint becomes available.
5. An OfflineGPT adapter if a stable local API becomes available.
6. Android device-control capabilities only after sandboxing, authentication, audit logging, and approval gates are implemented.
