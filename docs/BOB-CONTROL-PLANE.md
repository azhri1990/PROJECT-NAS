# PROJECT-BOB Control Plane

## Verification states

- `NOT_TRIGGERED`: no applicable CI evidence exists for the exact revision.
- `RUNNING`: an applicable CI run exists but has not completed.
- `FAILED`: the applicable CI run completed unsuccessfully.
- `VERIFIED`: the applicable CI run completed successfully for the exact revision.
- `ESCALATED`: automatic recovery is blocked because a known failure recurred or safety/verification evidence is insufficient.

`VERIFIED` is never inferred from a branch name, a previous successful run, a different commit SHA, or an empty legacy commit-status response.

## Failure-learning flow

```text
failure
  -> classify
  -> record lesson
  -> apply prevention
  -> retry only within the configured bound
  -> if the known failure recurs: ESCALATED
```

Every BOB failure is durable state, not conversational memory. The NAS learning loop records the task, strategy, failure class, context, source, lesson, and outcome evidence. Failure outcomes update the adaptive decision engine, while BOB escalation is scoped by `strategy_id + failure_class` so unrelated failures do not share one retry budget.

## Safe-stop rules

BOB stops and escalates when authorization is unclear, verification evidence is missing or mismatched, a known failure repeats after prevention, or an operation falls outside the bounded task policy.

## Routine autonomy

Routine build, test, verification, and bounded recovery actions do not require repeated human approval. Destructive, security-sensitive, architectural, or cost-changing actions remain explicit decision points for Nash.

## CI trigger contract

Runtime integration runs on `main`, on `bob/**` branch pushes, and on pull requests. A successful workflow run must be tied to the exact `head_sha` under test before BOB can report `VERIFIED`. The combined commit-status API is not the authoritative Actions execution signal.

## 24/7 target

The operational target is persistent supervisory capability, durable state, bounded recovery, and safe escalation across PC, tablet, and mobile/Termux. This does not promise that Android will keep one process alive indefinitely against OS lifecycle controls.
