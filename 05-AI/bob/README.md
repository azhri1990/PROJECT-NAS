# PROJECT-BOB Control Plane

PROJECT-BOB is the mobile-first orchestration layer for PROJECT-NAS.

## Contract

- GitHub is the source of truth.
- BOB routes work; it does not bypass PROJECT-NAS policy.
- Capability records are advisory metadata only.
- Device availability is explicit and observable.
- Jobs are deterministic, serializable, and resumable.
- External AI workers are optional; zero-cost/local workers are preferred.

## Device roles

- `android`: command/control, Termux execution, lightweight jobs.
- `tablet`: review, documentation, lightweight jobs.
- `pc`: heavy build/test/runtime jobs.

## BOB-2 mobile command channel

The command API is a private FastAPI surface exposed by `runtime/bob_command_api.py`.
Set `PROJECT_BOB_AUTH_TOKEN` on the BOB host. Clients send `Authorization: Bearer <token>`.

Endpoints:

- `GET /health` — liveness; no authentication.
- `POST /jobs` — submit a bounded task and capability.
- `GET /jobs/{job_id}` — inspect state.
- `POST /jobs/{job_id}/cancel` — cancel before execution begins.
- `GET /workers` — list registered workers.
- `POST /workers/heartbeat` — register/update worker availability.

Example mobile request:

```bash
curl -H "Authorization: Bearer $PROJECT_BOB_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task":"inspect repository status","capability":"read_repository"}' \
  http://127.0.0.1:8000/jobs
```

The command API does not expose arbitrary shell execution. Submitted capabilities are evaluated by the existing `PolicyEngine`; process execution, network access, and repository writes remain denied by default.

## BOB-3 autonomous orchestration

`07-AUTOMATION/bob/autonomous_orchestrator.py` adds deterministic, resource-aware scheduling. Workers report a `ResourceSnapshot`; BOB may defer work when CPU, memory, or local inference requirements are not satisfied. Failures use a bounded retry budget and transition to a failed/blocked state when exhausted.

BOB-3 remains an orchestrator: it does not execute arbitrary commands or grant permissions. Worker execution and PROJECT-NAS `PolicyEngine`/`ToolGateway` remain authoritative.

## Safety boundary

BOB may select a worker and create a job specification, but execution authority remains with the existing PROJECT-NAS policy/tool gateway. No credential, bearer token, unrestricted shell permission, or policy override belongs in the BOB registry.
