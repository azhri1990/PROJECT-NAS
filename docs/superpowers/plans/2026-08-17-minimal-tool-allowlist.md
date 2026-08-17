# Minimal Tool Allowlist Implementation Plan

## Goal
Restrict PROJECT-NAS tool execution to an explicit minimal allowlist.

Allowed namespaces:
- memory.*
- prompt.*
- status.*

Everything else is denied by default.

## Security invariants

1. Namespace authorization happens before input validation and handler execution.
2. Unknown tools are denied.
3. shell.* is denied.
4. process.* is denied.
5. plugin.* is denied.
6. custom.* is denied.
7. network.* is denied.
8. repo.* is denied unless deliberately migrated into status.*.
9. No arbitrary Python/module/plugin execution.
10. No dynamic plugin discovery/loading.
11. Existing non-gateway functionality remains intact.
12. Full pytest suite remains passing.
13. runtime/doctor.py remains HEALTHY.
14. git diff --check remains clean.

## Implementation

### Task 1 — Tests

Add regression tests proving memory.*, prompt.*, and status.* are allowed.
Add regression tests proving shell.*, process.*, plugin.*, custom.*, network.*, repo.*, and unknown namespaces are denied.
Prove denied tools never invoke their validators or handlers.
Preserve existing validation, timeout, audit, serialization, and capability-policy tests.

### Task 2 — Gateway

Add an explicit namespace allowlist to ToolGateway.
The namespace gate must execute before input validation and handler dispatch.

### Task 3 — Default gateway

Remove repo.progress from the default gateway unless deliberately redesigned as a status.* read operation.
Do not rename it merely to bypass the allowlist.

### Task 4 — Verification

Run the tool-gateway tests, full pytest suite, runtime doctor, git diff --check, and git status.
