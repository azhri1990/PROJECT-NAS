# BOB-2 Mobile Command Channel Design

## Goal
Provide a private, authenticated mobile command interface for PROJECT-BOB without bypassing the existing PROJECT-NAS PolicyEngine or ToolGateway.

## Boundary
The command channel accepts bounded job metadata, routes work through the existing BOB queue/router, and records audit events. It does not expose arbitrary shell execution, credentials, or a public-internet listener.

## API
- `GET /health` — unauthenticated liveness check.
- `POST /jobs` — authenticated job submission.
- `GET /jobs/{job_id}` — authenticated status lookup.
- `POST /jobs/{job_id}/cancel` — authenticated cancellation for cancellable states.
- `GET /workers` — authenticated worker inventory.
- `POST /workers/heartbeat` — authenticated worker availability update.

## Authentication
Use an operator token supplied through `PROJECT_BOB_AUTH_TOKEN`. Requests use `Authorization: Bearer <token>`. Missing server configuration fails closed for authenticated endpoints. Token comparison uses constant-time comparison.

## Policy
A submitted capability must map to an existing `runtime.policy.Capability`. The existing `PolicyEngine` evaluates the request before the job is accepted. Process execution, network access, repository writes, and high-risk requests therefore remain denied by the current default policy.

## Lifecycle
Jobs begin in `created`, become `queued` after policy approval, and are routed to a capable online worker. Jobs without a worker become `blocked`. Cancellation is allowed only before a job enters `running`.

## Security constraints
- No shell endpoint.
- No arbitrary tool name execution.
- No credential storage in repository files.
- No public-network exposure requirement.
- Audit records contain identifiers and decisions, not bearer tokens.

## Success criteria
Authenticated mobile clients can submit, inspect, and cancel bounded jobs; workers can heartbeat; policy-denied capabilities are rejected; unauthorized requests fail; all behavior is covered by automated tests.