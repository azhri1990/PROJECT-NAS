# Autopilot remediation

This document records the zero-cost remediation tranche for the local/mobile runtime.

- Controller-owned processes are stopped only when ownership identity matches.
- Externally managed services are never terminated by the controller.
- A stop with no services present is successful.
- Runtime dependencies remain pure-Python on Termux; optional native desktop dependencies are separated.
