# PROJECT-NAS Rectification Gate — 2026-08-18

Before adding new user-facing capabilities, the local orchestration path must be deterministic under failure.

## Required invariants

- Model execution stays loopback-only.
- User input remains bounded before context composition.
- Context remains bounded before model execution.
- Transport failures are distinguishable from model HTTP availability failures.
- Configured-model fallback may occur only for expected model-unavailable responses.
- Timeout/network failures must not silently select another model.
- Non-object Ollama responses are rejected.
- Successful model responses must contain a usable response field before being exposed upstream.
- Model output has a deterministic character ceiling.

## Next build gate

Harden local-model failure semantics and add regression coverage before adding voice/mobile/UI capabilities.
