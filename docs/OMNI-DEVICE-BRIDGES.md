# PROJECT-NAS Omni Device AI Bridges

This document records the verified integration boundary for the six Android/mobile AI applications currently being evaluated for PROJECT-NAS.

## Architecture rule

PROJECT-NAS remains the orchestrator, policy owner, memory owner, and audit boundary. Mobile applications are capability providers or operator surfaces. They do not receive unrestricted PROJECT-NAS authority.

The first bridge uses the OpenAI-compatible HTTP contract for endpoints that actually expose that contract. Ollama Local AI is a verified example. Hermes Agent - Android is **not** treated as an API server merely because the underlying Hermes ecosystem has an OpenAI-compatible server; the Android app itself is treated as a device/agent surface until its machine-readable integration boundary is explicitly verified.

## Integration matrix

| App | Role in PROJECT-NAS | v1 status | Integration boundary |
| --- | --- | --- | --- |
| Ollama Local AI | Android/local model gateway | Supported | OpenAI-compatible `/v1` endpoint; explicit URL required |
| Hermes Agent - Android | Android agent/device runtime | Optional | Built-in terminal/code/memory plus beta PC companion; no direct PROJECT-NAS API assumed |
| Hermes-Relay | Android client/relay surface | Optional | Talks to a configured Hermes instance; not a model provider |
| Codex Mobile | Browser/app-server coding surface | Optional | Operator surface; no direct PROJECT-NAS execution contract assumed |
| PocketPal AI | On-device local inference | Unverified | No remote PROJECT-NAS API is assumed |
| OfflineGPT | On-device offline inference | Unverified | No remote PROJECT-NAS API is assumed |

A separate `custom-openai-compatible` adapter is included for a verified OpenAI-compatible server. This can be used later for a separately operated Hermes API server without falsely representing the Android Hermes app as the server.

## Environment configuration

Only explicitly configured endpoints are enabled.

```text
PROJECT_NAS_OMNI_OLLAMA_URL=http://192.168.1.20:11434/v1
PROJECT_NAS_OMNI_OLLAMA_MODEL=qwen3
PROJECT_NAS_OMNI_OLLAMA_API_KEY_ENV=

PROJECT_NAS_OMNI_COMPAT_URL=http://192.168.1.30:8642/v1
PROJECT_NAS_OMNI_COMPAT_MODEL=hermes-agent
PROJECT_NAS_OMNI_COMPAT_API_KEY_ENV=HERMES_API_SERVER_KEY

PROJECT_NAS_OMNI_ALLOWED_HOSTS=192.168.1.20,192.168.1.30
```

Do not place the API key itself in these settings. `*_API_KEY_ENV` contains the name of an environment variable whose value is read only at request time.

Loopback endpoints are permitted for local development. LAN or public hosts must be explicitly allowlisted.

## Hermes Agent - Android boundary

The Hen Works Android app provides a built-in Linux terminal, Python/bash/git execution, memory, multiple AI providers, and beta cross-device collaboration with an open-source PC companion. The PC companion can dispatch tasks from the phone and supports desktop handoff. PROJECT-NAS will treat this as a device/agent capability boundary, not as a trusted backend.

Before PROJECT-NAS delegates commands to Hermes, the next security milestone must add explicit capability discovery, authentication, approval policy, audit logging, and sandboxing.

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

1. Hermes Agent Android PC-companion pairing through its documented encrypted mesh boundary.
2. Hermes capability discovery where a verified Hermes API server is used.
3. Explicit PROJECT-NAS policy checks before delegated tool execution.
4. Codex task delegation through a stable app-server contract if one is selected and verified.
5. A PocketPal adapter if a stable OpenAI-compatible endpoint becomes available.
6. An OfflineGPT adapter if a stable local API becomes available.
7. Android device-control capabilities only after sandboxing, authentication, audit logging, and approval gates are implemented.
