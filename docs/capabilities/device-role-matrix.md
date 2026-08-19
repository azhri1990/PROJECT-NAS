# PROJECT-NAS Device Role Matrix

**Snapshot:** 2026-08-20

| Role | Primary purpose | Preferred components | Failure posture |
|---|---|---|---|
| `ANDROID_EDGE` | Control, approvals, lightweight scripts, local edge work | Termux, Codex Mobile, Hermes/OpenClaw clients | Queue work when PC or GitHub is unavailable; do not become a second source of truth |
| `TABLET_EDGE` | Review, dashboard, documentation, UI work | Codex, Figma, Obsidian/Notion | Review/control surface; avoid heavy runtime workloads |
| `PC_BUILD` | Primary build, test, repository workspace, heavy local inference | GitHub checkout, Codex, Python, pytest, Ollama | Primary execution target; BOB can queue when PC is offline |
| `GITHUB_SOURCE` | Source-of-truth synchronization and collaboration | GitHub | If unavailable, continue only with local work already present; do not silently diverge histories |
| `NAS_RUNTIME` | Governed execution, memory, orchestration, tool gateway | Existing PROJECT-NAS runtime | Fail closed on unknown policy/tool state |

## Data flow

```text
Android / Tablet
      |
      v
PROJECT-BOB control plane
      |
      +----> GitHub source of truth
      |
      +----> PC build/test + Ollama
      |
      +----> governed worker selection
      |
      v
PROJECT-NAS runtime
      |
      +---- PolicyEngine
      +---- ToolGateway
      +---- Orchestration
      +---- Memory
      +---- Verification
```

## Fallback rules

- **PC offline:** BOB may collect tasks and perform bounded edge work; heavy builds remain queued.
- **GitHub unavailable:** BOB may continue local non-destructive work, but must not claim repository synchronization.
- **Ollama unavailable:** use another already-authorized local model if present; otherwise queue model-dependent work.
- **Worker unavailable:** select the next authorized candidate; if no candidate is verified, fail closed.
- **Android offline:** PC remains capable of continuing repository/build work.
- **Tablet offline:** no core capability is lost.

## Security boundary

The app capability registry is advisory metadata. It does not grant filesystem, shell, network, credential, or repository permissions. Actual execution remains controlled by PROJECT-NAS's existing policy and tool gateway.
