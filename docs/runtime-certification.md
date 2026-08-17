# PROJECT-NAS Runtime Certification

## Gate

A runtime certification requires all of the following to pass:

1. Full Python regression suite.
2. Runtime-controller regression suite.
3. Shell syntax and Python compilation checks.
4. Repository whitespace check.
5. PROJECT-NAS doctor diagnostics.
6. Termux smoke test with the real local Ollama runtime.

## Zero-cost constraint

The certification path must not require paid APIs, hosted model credits, or mandatory cloud services. CI uses local deterministic test behavior; real device certification uses the user's local Termux/Ollama stack.

## Status

This gate is intentionally not considered green until both CI and real-device validation pass.
