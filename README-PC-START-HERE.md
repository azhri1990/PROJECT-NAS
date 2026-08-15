# PROJECT-NAS — PC Start Here

This folder is the mobile-to-PC continuity package.

Start with:
1. `ai/Nash_Consolidated_AI_Operating_System_and_Profile.md`
2. `ai/MASTER_PROMPT.md`
3. `profile/comprehensive_profile.md`
4. `runtime/project-nas.sh`
5. `runtime/memory_injector.py`
6. `runtime/omni/`
7. `docs/OMNI-DEVICE-BRIDGES.md`
8. `TRANSFER-MANIFEST.md`

## Omni mobile AI bridge

PROJECT-NAS can now discover and health-check explicitly configured OpenAI-compatible local/mobile endpoints. The first supported bridge targets Ollama Local AI and Hermes Agent. Hermes-Relay and Codex Mobile remain operator/device surfaces; PocketPal and OfflineGPT remain optional until a verified machine-readable API is available.

Example environment configuration:

```text
PROJECT_NAS_OMNI_OLLAMA_URL=http://192.168.1.20:11434/v1
PROJECT_NAS_OMNI_OLLAMA_MODEL=qwen3
PROJECT_NAS_OMNI_HERMES_URL=http://192.168.1.30:8642/v1
PROJECT_NAS_OMNI_HERMES_MODEL=hermes-agent
PROJECT_NAS_OMNI_HERMES_API_KEY_ENV=HERMES_API_SERVER_KEY
PROJECT_NAS_OMNI_ALLOWED_HOSTS=192.168.1.20,192.168.1.30
```

Keep provider secrets in environment variables, not source files. Loopback is allowed for local development; LAN/public hosts must be explicitly allowlisted.

## Important

Do not overwrite the GitHub repository blindly. First inspect the repository and reconcile these artifacts against the actual checkout. The Omni bridge is intentionally an adapter layer so the original Omni Core architecture can be upgraded later without replacing the runtime.
