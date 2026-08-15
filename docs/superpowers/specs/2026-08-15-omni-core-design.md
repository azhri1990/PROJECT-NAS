# PROJECT-NAS Omni Core v1 — Design Specification

**Date:** 2026-08-15  
**Status:** Design proposed for review  
**Constraint:** $0 recurring cost; local-first; no required paid AI/API subscription

## 1. Objective

Evolve PROJECT-NAS from a collection of local runtime services into a modular Omni Core that can route work to local models, coordinate specialist review passes, use bounded tools, manage context and memory, and verify proposed actions before execution.

The design intentionally adopts architectural principles visible in modern agent systems—model/tool/instruction separation, orchestration, guardrails, observability, sandboxed execution, memory and context management—without depending on proprietary cloud infrastructure.

## 2. Non-goals

- Training a frontier model from scratch.
- Reproducing proprietary OpenAI implementation details.
- Requiring paid cloud inference.
- Giving an LLM unrestricted shell, filesystem, network, GitHub, or credential access.
- Claiming the system is literally unhackable or flawless.

## 3. Proposed architecture

```text
User / Trigger
     |
     v
Omni Router ----> Context Manager ----> Memory Policy
     |
     v
Task Planner
     |
     +---- Builder Agent
     +---- Skeptic Agent
     +---- Security Agent
     +---- Test/Cost Agent
     |
     v
Debate / Arbitration Layer
     |
     v
Policy + Permission Gate
     |
     +---- Read-only tools
     +---- Controlled write tools
     +---- Sandboxed execution
     |
     v
Verification Engine
     |
     +---- unit/integration tests
     +---- security checks
     +---- repository checks
     |
     v
Result / Human escalation
```

## 4. Core components

### 4.1 Omni Router

Select the cheapest capable local model and workflow based on task type, available resources, and failure state. The router must have deterministic fallback rules and must never silently switch to a paid provider.

### 4.2 Task Planner

Convert a request into bounded steps, explicit success criteria, required tools, risk classification, and a verification plan. Planning output is data and cannot directly execute tools.

### 4.3 Specialist review passes

For medium/high-risk work, run independent perspectives before application:

1. **Builder:** simplest viable solution.
2. **Skeptic:** attempts to falsify the proposal and identify regressions.
3. **Security:** attacks trust boundaries, injection paths, data exposure, privilege escalation, and unsafe execution.
4. **Test/Cost:** identifies proof requirements, resource limits, and $0/local-first violations.

These are logical roles. They may use the same local model with different prompts, or different local models when resources permit. The system must not claim independent intelligence merely because prompts are different.

### 4.4 Arbitration

A deterministic policy layer compares proposals against requirements. For high-risk changes, disagreement blocks execution until a revised proposal satisfies the required checks or receives explicit human approval.

### 4.5 Tool gateway

Every tool has a typed contract, capability declaration, input validation, timeout, resource limit, and audit event. Tools are divided into data/read, action/write, and orchestration capabilities.

### 4.6 Execution isolation

Code generated or selected by an agent executes in a restricted workspace. Credentials remain outside the execution environment. Network access is disabled unless explicitly required by a policy-approved tool.

### 4.7 Context manager

Keep the model payload bounded. Prioritize task state, relevant files, recent decisions, and high-confidence memory. Compress or summarize older context instead of continually appending raw history.

### 4.8 Memory policy

Automatic memory writes are not trusted by default. Memory must pass classification and redaction rules, carry provenance and timestamps, support retention/deletion, and be injected as untrusted data rather than instructions.

### 4.9 Verification engine

A change is complete only after the appropriate checks pass. Fast checks run first; expensive checks run only when the change warrants them. Verification results are recorded for auditability.

## 5. Security model

PROJECT-NAS follows defense in depth rather than an “unhackable” claim:

- Local-only network exposure by default.
- Least privilege for tools and plugins.
- Strict path and argument validation.
- No arbitrary command execution from model output.
- Explicit approval for destructive or irreversible actions.
- Prompt injection treated as an expected threat.
- Retrieved memory and external content treated as untrusted data.
- Credentials never placed in model context unless a narrowly scoped tool requires them.
- Timeouts, size limits, retry limits, and circuit breakers for resource exhaustion.
- Immutable/auditable action records where practical.
- Dependency and security scanning in CI.

## 6. Failure handling

The system must distinguish:

- model failure
- tool failure
- environment failure
- policy rejection
- test failure
- security finding
- insufficient evidence

A failed model should trigger deterministic fallback routing where safe. A failed security or policy gate must not be bypassed by fallback models.

## 7. Performance strategy

Optimize for time-to-verified-result:

- Fast model for triage and simple work.
- Parallel specialist reviews when useful.
- Batch compatible inspections.
- Targeted tests before full CI.
- Cache stable metadata and context summaries locally.
- Avoid repeated repository scans when the affected scope is known.
- Escalate to deeper reasoning only when risk or uncertainty justifies it.

## 8. Testing strategy

Each subsystem gets unit tests. Cross-system behavior gets integration tests. Security-sensitive boundaries get adversarial tests. The Omni Core itself gets scenario tests covering:

- conflicting specialist recommendations
- prompt injection in repository files
- malicious plugin names/paths
- tool authorization failures
- model timeout/OOM/fallback
- oversized context
- memory poisoning attempts
- destructive-action approval requirements
- failed verification and retry limits

## 9. Acceptance criteria for v1

The first implementation milestone is accepted only when:

1. A request can be classified and routed to a local model.
2. Medium/high-risk changes trigger independent specialist review passes.
3. No specialist can directly bypass the tool/policy gate.
4. Tools expose explicit capabilities and validation.
5. Model-generated code cannot access unrestricted host credentials.
6. Context and memory are bounded and policy-controlled.
7. Failed checks block application.
8. The system can fall back to another local model or degrade gracefully without paid services.
9. CI proves the critical paths on a clean environment.
10. Documentation accurately describes implemented behavior versus roadmap items.

## 10. Debate result

### Builder view

A modular router + planner + tool gateway + verifier provides the largest capability gain without rewriting the existing runtime.

### Skeptic view

A large multi-agent framework too early would add latency, duplicated context, and failure modes. Start with logical specialist roles and only parallelize where it measurably improves quality.

### Security view

The most dangerous expansion is unrestricted tool execution and automatic memory writes. Both must be policy-gated before broader autonomy.

### Cost/performance view

Multiple local agents can multiply RAM/VRAM usage. The router must support sequential execution, model reuse, and resource-aware degradation. $0 means no mandatory cloud fallback.

### Arbitration

Proceed with a **small Omni Core kernel**, not a giant framework. Reuse the existing FastAPI backend, memory layer, tests, and Doctor diagnostics. Add policy/tool/context abstractions behind stable interfaces. Defer voice, remote device control, autonomous deployment, and broad plugin ecosystems until the security and verification foundation is proven.

## 11. Implementation order

1. Policy/capability primitives.
2. Tool gateway with read-only tools first.
3. Specialist review orchestration.
4. Arbitration and verification contracts.
5. Context budgeting/compression.
6. Memory classification/redaction/retention.
7. Resource-aware local model routing and fallback.
8. Sandboxed execution.
9. Adversarial security suite.
10. Broader autonomous capabilities only after the above gates pass.
