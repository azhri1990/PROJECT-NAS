# Runtime Certification Gate

Green requires both automated lifecycle proof and a real Termux/Ollama smoke test.

Automated CI proves: start, status, health, canonical chat, doctor, stop, and backend termination using loopback-only temporary mocks.

The real-device gate proves the same path against the user's local Ollama and memory services, including model response and restart/recovery.

This remains a $0/local-first architecture with no required paid API or hosted model.
