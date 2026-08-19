# PROJECT-BOB BOB-4 Worker Protocol

BOB-4 provides a local/private-network HTTP protocol for Android/Termux, PC, and tablet workers.

## Security boundary

Workers authenticate to BOB, but worker registration and capability advertisement never grant execution authority. A job claim is evaluated by the existing PROJECT-NAS `PolicyEngine` before a lease is issued. The policy engine remains the final authority.

The service deliberately exposes no arbitrary shell or command endpoint.

## Authentication

Set `PROJECT_BOB_AUTH_TOKEN` in the BOB service environment. Requests must send:

```text
Authorization: Bearer <token>
```

If the token is missing, the service fails closed with HTTP 503. Missing or invalid request authentication returns HTTP 401.

Never commit a token to GitHub or include it in audit events.

## Worker lifecycle

1. `POST /workers/register` registers a worker identity, platform, capabilities, and resource snapshot.
2. `POST /workers/heartbeat` refreshes availability and resources.
3. `POST /jobs/claim` requests a job lease. BOB checks worker registration/capability and NAS policy before issuing the lease.
4. Worker performs only the task authorized by the surrounding NAS execution contract.
5. `POST /jobs/result` reports `succeeded`, `failed`, or `cancelled` using the job and lease IDs.
6. If the lease expires, BOB releases it for safe reclamation and records a `job_requeued` audit event.
7. Repeated result submission for an already-completed lease is idempotent.

## Endpoints

### Register

`POST /workers/register`

```json
{
  "worker_id": "android-1",
  "platform": "android",
  "capabilities": ["read_repository"],
  "resources": {"memory_mb": 2048},
  "now": 100
}
```

### Heartbeat

`POST /workers/heartbeat`

```json
{"worker_id": "android-1", "resources": {"memory_mb": 2048}, "now": 110}
```

### Claim

`POST /jobs/claim`

```json
{"job_id": "job-1", "worker_id": "android-1", "capability": "read_repository", "now": 111}
```

The client cannot supply a `policy_allowed` flag. BOB evaluates NAS policy itself.

### Result

`POST /jobs/result`

```json
{
  "job_id": "job-1",
  "lease_id": "<opaque lease id>",
  "worker_id": "android-1",
  "status": "succeeded",
  "output": {"ok": true},
  "now": 120
}
```

### Worker inventory

`GET /workers` returns registered worker identity, platform, status, capabilities, and last-seen time. It never returns authentication credentials.

## Platform adapters

- `runtime/bob/workers/android_termux.py` — Android/Termux identity adapter.
- `runtime/bob/workers/pc.py` — PC identity adapter.
- `runtime/bob/workers/tablet.py` — tablet identity adapter.

These adapters contain no privileged execution code or embedded credentials.

## Network posture

Keep the service on localhost or a trusted private network during the initial deployment. Do not expose the BOB worker API directly to the public Internet. A future relay can provide remote connectivity without changing the worker protocol's policy boundary.

## Cost model

BOB-4 adds no paid API, cloud GPU, or mandatory external service. It is designed for local/self-hosted workers and the existing GitHub CI workflow.
