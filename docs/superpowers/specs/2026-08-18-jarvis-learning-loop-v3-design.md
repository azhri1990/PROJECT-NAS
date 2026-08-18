# JARVIS Learning Loop v3

## Goal
Turn observed task outcomes into measurable, bounded improvements in JARVIS strategy selection without allowing learned data to grant capabilities, alter security policy, or self-modify executable code.

## Constraints
- $0 / local-first: SQLite and existing local runtime only.
- No paid API, token-credit, or cloud dependency.
- Learning is evidence-driven and reversible.
- UNKNOWN outcomes do not train the system.
- Security/capability authority remains outside the learning subsystem.
- Existing certification gates remain authoritative.

## Architecture
A small `LearningLoopV3` coordinator records observations, evaluates outcomes, stores lessons and strategy feedback, consolidates duplicate evidence, and exposes bounded metrics. It composes the existing `SecondBrain`, `StrategyMemory`, `AdaptiveDecisionEngine`, and `CognitiveMemoryStore` rather than replacing them.

The loop is deterministic: observation -> evaluation -> reflection -> consolidation -> adaptation -> measurement. Adaptation only changes ranking/confidence; execution authorization remains governed by the existing orchestration policy.

## Safety
- Reject empty/oversized inputs.
- Never persist UNKNOWN as positive/negative evidence.
- Never auto-pin memory.
- Never mutate policy/capability authority.
- Record provenance for every promoted lesson.
- Keep maintenance bounded and local.

## Verification
Tests must cover successful learning, failed learning, UNKNOWN no-op behavior, duplicate consolidation, metrics, and preservation of capability boundaries. The full repository pytest suite, Python compilation, doctor, and certification script remain the final acceptance gates.
