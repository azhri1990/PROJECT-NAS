# PROJECT-NAS Capability Matrix Design

**Date:** 2026-08-20
**Status:** Approved for implementation planning

## Goal

Create a governed capability inventory for the user's Android, tablet, and PC app ecosystem so PROJECT-NAS and PROJECT-BOB can distinguish core infrastructure, delegated worker tools, creative tools, backups, personal apps, and unnecessary/risky integrations.

## Scope

The first implementation covers the supplied Android app inventory and maps each app to capability, platform role, integration value, security sensitivity, redundancy, and disposition. The system must not require every installed app to integrate with PROJECT-NAS.

## Architecture

The capability matrix is a data-driven registry consumed by documentation and future BOB policy/orchestration. Core infrastructure remains small and local-first: GitHub, Codex, Termux, Ollama, and the existing NAS runtime. External AI services are optional workers rather than hard dependencies. Device automation must pass through governed tool/policy boundaries instead of granting arbitrary app access to the repository or credentials.

## Core classifications

- **CORE:** required or directly valuable to build/run NAS or BOB.
- **WORKER:** an external AI/agent/model service that can perform delegated work but is not authoritative.
- **TOOL:** useful for a bounded task such as design, media, documentation, or research.
- **BACKUP:** redundant capability retained for resilience or model diversity.
- **PERSONAL:** unrelated to NAS engineering.
- **IGNORE:** duplicate, low-value, unclear, or unnecessarily risky for the NAS ecosystem.

## Governance rules

1. PROJECT-NAS remains the source of truth.
2. No app becomes a runtime dependency merely because it is installed.
3. Local/self-hosted tools are preferred where capability is equivalent.
4. Secrets and tokens never enter the capability registry.
5. Agent/device access is least-privilege and mediated by policy/tool gateways.
6. Learning and orchestration may select workers but cannot grant new capabilities.
7. External network actions remain denied or confirmation-gated unless explicitly governed.
8. The matrix must record evidence/status rather than inventing integration support.
9. Android is treated as a control/edge execution environment; the PC remains the preferred heavy build/inference machine where available.
10. The first release is inventory and governance; automatic control of arbitrary third-party apps is explicitly out of scope.

## Initial role model

```text
Android / Tablet
  -> control, Termux, edge scripts, relay/agent clients

PC
  -> primary build/test machine, local Ollama inference, repository workspace

GitHub
  -> source-of-truth repository and collaboration boundary

PROJECT-BOB
  -> governed orchestrator that selects workers and executes approved tasks

PROJECT-NAS runtime
  -> policy, memory, orchestration, tool gateway, verification
```

## Success criteria

- Every supplied app has one disposition and a concise reason.
- Core tools are explicitly separated from optional workers and personal apps.
- Security-sensitive integrations are identified before any connector is enabled.
- The matrix can be extended without changing runtime code.
- Tests verify classification schema, duplicate handling, and policy invariants.
- Documentation explains how the matrix maps to Android, tablet, PC, BOB, and NAS.
