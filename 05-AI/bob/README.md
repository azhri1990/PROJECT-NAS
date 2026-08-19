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

## Safety boundary

BOB may select a worker and create a job specification, but execution authority remains with the existing PROJECT-NAS policy/tool gateway. No credential, bearer token, unrestricted shell permission, or policy override belongs in the BOB registry.
