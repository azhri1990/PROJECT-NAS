# PROJECT-BOB Control Plane

## Verification states

- `NOT_TRIGGERED`: no applicable CI evidence exists for the exact revision.
- `RUNNING`: an applicable CI run exists but has not completed.
- `FAILED`: the applicable CI run completed unsuccessfully.
- `VERIFIED`: the applicable CI run completed successfully for the exact revision.
- `ESCALATED`: automatic recovery is blocked because a known failure recurred or safety/verification evidence is insufficient.

`VERIFIED` is never inferred from a branch name, a previous successful run, or a different commit SHA.

## Failure-learning flow

```text
failure
  -> classify
  -> record lesson
  -> apply prevention
  -> retry only within the configured bound
  -> if the known failure recurs: ESCALATED
```

Lessons are durable state, not conversational memory.

## Safe-stop rules

BOB stops and escalates when authorization is unclear, verification evidence is missing or mismatched, a known failure repeats after prevention, or an operation falls outside the bounded task policy.

## Routine autonomy

Routine build, test, verification, and bounded recovery actions do not require repeated human approval. Destructive, security-sensitive, architectural, or cost-changing actions remain explicit decision points for Nash.

## CI trigger contract

Runtime integration runs on `main`, on `bob/**` branch pushes, and on pull requests. A successful PR check is still evaluated against the exact revision under test before BOB can report `VERIFIED`.
