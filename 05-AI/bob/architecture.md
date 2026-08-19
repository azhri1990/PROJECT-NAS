# BOB Control Plane Architecture

```text
Nash / mobile
      |
      v
    BOB
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

`created -> queued -> dispatched -> running -> succeeded|failed|blocked`

A job can be resumed from its persisted specification. A worker is selected from declared capabilities and availability; BOB never assumes a device is online.

## Routing priority

1. Local/zero-cost worker.
2. Matching online device with lowest declared cost.
3. Explicit fallback worker.
4. Otherwise `blocked` with a reason.

## Risk

Routing is not authorization. A selected worker still requires the normal PROJECT-NAS policy/tool gateway checks before execution.
