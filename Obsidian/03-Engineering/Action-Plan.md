# Engineering Action Plan

## Definition of done

A feature is complete only when it is executable, tested, accurately documented and reproducible on a clean environment.

## Priority queue

- [ ] Run the complete CI suite after the latest changes.
- [ ] Add end-to-end `/chat` tests with fake local Ollama and isolated Chroma.
- [ ] Add model discovery and health checks.
- [ ] Add deterministic fallback routing.
- [ ] Add context budgeting/compression.
- [ ] Define memory retention and redaction policy.
- [ ] Perform repository-wide security review.
- [ ] Only then expand plugin, remote-device and integration surfaces.

## Decision rule

When choosing between a new feature and reliability work, protect the runtime foundation first. Avoid adding UI/automation complexity on top of unverified core behavior.

Source: `ACTION-PLAN.md`
