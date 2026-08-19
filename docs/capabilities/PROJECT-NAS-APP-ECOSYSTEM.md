# PROJECT-NAS App Ecosystem

**Inventory snapshot:** 2026-08-20

## Operating model

```text
Android phone  -> control / edge execution / approvals
Tablet         -> review / UI / documentation
PC             -> primary build / test / Ollama inference
GitHub         -> source of truth
PROJECT-BOB    -> governed orchestrator
PROJECT-NAS    -> policy / tools / memory / verification
```

The supplied app inventory is now classified in `app-capability-matrix.json`. The matrix deliberately separates **capability** from **authorization**: an app can be useful without receiving access to the repository, filesystem, shell, credentials, or network.

## Core

The core engineering path is intentionally small:

- GitHub — source control and collaboration boundary.
- Codex — primary engineering agent.
- Codex Mobile/Web — mobile/remote engineering surfaces.
- Termux — Android Linux/Python/Git/SSH substrate.
- Ollama Local AI — local inference.
- OpenClaw/Hermes components — candidate governed device/relay layer.
- Existing PROJECT-NAS runtime — policy, tool gateway, orchestration, memory, and verification.

## Workers

Claude, Gemini, DeepSeek, Kimi, Copilot, Perplexity, Grok, Qwen Studio, MiniMax, Manus, Genspark, Replit, Base44, Lovable, Omni Coder and similar apps are **workers**, not authorities. BOB may recommend them for bounded tasks only when an integration is explicitly authorized.

## Creative/tool layer

Figma, Canva, Adobe tools, image generators, video editors, Obsidian, Notion, transcription, and similar applications are task-specific tools. They should produce artifacts that return to the PROJECT-NAS source-of-truth workflow rather than becoming hidden state stores.

## Personal/noise layer

Messaging, companion, ringtone, sticker, wallpaper, and generic chatbot applications remain outside the engineering runtime. They do not need to be uninstalled; they simply do not belong in the BOB capability path.

## Security rule

No capability record may contain bearer tokens, API keys, credentials, unrestricted permissions, executable commands, or policy overrides. Unknown or malformed capability data fails closed.
