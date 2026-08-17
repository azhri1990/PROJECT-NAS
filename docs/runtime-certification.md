# PROJECT-NAS Runtime Certification

The repository is considered operationally green only when the runtime smoke workflow proves the canonical local path without paid or cloud services.

## Gate

1. Controller starts the backend.
2. Local dependency endpoints are reachable on loopback.
3. Backend `/health` reports `healthy`.
4. Backend `/chat` returns a response through the canonical worker path.
5. Doctor diagnostics complete successfully.
6. Controller stop removes its backend process.
7. The backend is no longer reachable after stop.

The CI smoke job uses temporary loopback-only mock services. It does not replace the real Termux/Ollama test; it proves the controller and backend lifecycle deterministically on GitHub Actions. The final mobile gate remains a real-device smoke test with Ollama.

All components remain compatible with the project's $0 local-first requirement.
