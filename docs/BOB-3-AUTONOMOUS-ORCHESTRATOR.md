# PROJECT-BOB — BOB-3 Autonomous Orchestrator

## Purpose

BOB-3 adds resource-aware scheduling and bounded recovery to the PROJECT-BOB control plane. It is designed for mobile-first supervision with Android, tablet, and PC workers.

## Guarantees

- BOB does not execute arbitrary commands.
- NAS `PolicyEngine` / `ToolGateway` remain the execution authority.
- Worker resource state is advisory scheduling input.
- CPU and memory constraints can defer work.
- Local-inference requirements can defer work when no inference provider is available.
- Retries are bounded by a configured retry budget.
- Exhausted retries fail closed rather than looping indefinitely.

## Zero-cost model

The orchestrator introduces no paid API, cloud GPU, or subscription dependency. Local workers and local inference are preferred; external AI workers remain optional.

## Lifecycle

`created -> running -> succeeded`

Failure recovery:

`running -> queued -> retry -> running`

When the retry budget is exhausted:

`running -> failed`

A missing worker at dispatch time is blocked rather than executed through an untrusted fallback.

## Resource inputs

Workers can report:

- online/offline state
- CPU load from 0.0 to 1.0
- available memory
- available storage
- local inference availability

These values influence scheduling only. They do not grant permissions.

## Next extension

A later BOB release can add a persistent worker heartbeat/resource bridge and a mobile dashboard. Those extensions must preserve the same fail-closed policy boundary.
