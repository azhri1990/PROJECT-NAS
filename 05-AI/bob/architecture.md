# BOB Control Plane Architecture

```text
Nash / mobile
      |
 authenticated command
      v
    BOB API
      |
  +---+----------------+
  |                    |
worker selection    job queue
  |                    |
  +---------+----------+
            v
     NAS policy gateway
            |
     approved execution
```

## Job lifecycle

`created -> queued -> dispatched -> running -> succeeded|failed|blocked|cancelled`

A job can be resumed from its persisted specification. A worker is selected from declared capabilities and availability; BOB never assumes a device is online.

## Mobile command API

`runtime/bob_command_api.py` provides authenticated endpoints for job submission, status, cancellation, worker listing, and worker heartbeat. Authentication uses `PROJECT_BOB_AUTH_TOKEN` and constant-time bearer-token comparison. `/health` is the only unauthenticated endpoint.

The API is intentionally bounded: it accepts task metadata and policy capabilities, not shell commands or arbitrary tool names.

## Routing priority

1. Local/zero-cost worker.
2. Matching online device with lowest declared cost.
3. Explicit fallback worker.
4. Otherwise `blocked` with a reason.

## Risk

Routing is not authorization. A selected worker still requires the normal PROJECT-NAS policy/tool gateway checks before execution. The default policy denies process execution, network access, and repository writes without explicit approval.