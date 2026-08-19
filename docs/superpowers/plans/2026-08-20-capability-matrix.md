# PROJECT-NAS Capability Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the supplied Android app inventory into a governed, testable PROJECT-NAS capability registry that assigns every app a role, platform use, integration value, and security disposition without making third-party apps runtime dependencies.

**Architecture:** Store the inventory as data/documentation rather than hard-coding app names into runtime policy. Add a small validation layer and tests for classification/schema invariants, then document the Android/tablet/PC control-plane mapping. PROJECT-BOB consumes the registry as advisory metadata; existing PolicyEngine/ToolGateway remain the authority for executable capabilities.

**Tech Stack:** Python 3.13, pytest, Markdown/JSON data, existing PROJECT-NAS runtime policy/tool gateway, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-20-capability-matrix-design.md`

## Global Constraints

- $0 / local-first; no paid cloud AI/API dependency.
- PROJECT-NAS remains the source of truth.
- Unknown verification results fail closed.
- Learning cannot grant capabilities or rewrite policy/code.
- External network and system mutation remain denied or confirmation-gated unless explicitly governed.
- No secrets, bearer tokens, API keys, or machine-specific paths are committed.
- Third-party apps are optional workers/tools, never implicit runtime dependencies.
- Android is an edge/control environment; PC is the preferred heavy build/inference environment.
- Existing doctor/certification/policy gates remain authoritative.

---

### Task 1: Create the canonical capability registry

**Files:**
- Create: `docs/capabilities/app-capability-matrix.json`
- Create: `docs/capabilities/README.md`

**Interfaces:**
- Registry records use: `name`, `classification`, `capabilities`, `platform_roles`, `integration`, `security`, `disposition`, `reason`.
- `classification` is one of `CORE`, `WORKER`, `TOOL`, `BACKUP`, `PERSONAL`, `IGNORE`.
- `disposition` is one of `KEEP`, `OPTIONAL`, `BACKUP_ONLY`, `IGNORE`, `REMOVE_CANDIDATE`.

- [ ] **Step 1: Add a failing schema-validation test for required fields and allowed enum values.**
- [ ] **Step 2: Run the focused test and verify it fails because the registry does not yet exist.**
- [ ] **Step 3: Add the canonical registry containing every app supplied by the user, with duplicate names preserved only once and an explicit reason for merged duplicates.**
- [ ] **Step 4: Populate the initial governed core set: GitHub, Codex, Codex Mobile/Web where applicable, Termux, Ollama Local AI, and the existing BOB/NAS agent/relay components; keep external AI services as workers unless a verified local integration exists.**
- [ ] **Step 5: Document the six classifications and the distinction between an installed app and a governed NAS capability.**
- [ ] **Step 6: Run the focused validation test and verify PASS.**
- [ ] **Step 7: Commit the registry and documentation.**

### Task 2: Add registry validation without coupling runtime policy to app names

**Files:**
- Create: `runtime/capability_registry.py`
- Create: `tests/test_capability_registry.py`
- Inspect: `runtime/policy.py`
- Inspect: `runtime/tool_gateway.py`

**Interfaces:**
- `load_capability_registry(path: str | Path) -> list[dict]` validates and returns normalized records.
- `validate_capability_registry(records: list[dict]) -> list[str]` returns deterministic validation errors; an empty list means valid.
- Runtime policy continues to govern actual executable tools; registry metadata cannot grant permissions.

- [ ] **Step 1: Write tests for valid records, invalid classification, missing required fields, duplicate canonical names, and an attempted capability escalation field.**
- [ ] **Step 2: Run the focused tests and verify they fail before implementation.**
- [ ] **Step 3: Implement deterministic validation with no network calls and no third-party dependencies.**
- [ ] **Step 4: Explicitly reject records that contain executable permissions, credentials, unrestricted filesystem access, or policy overrides as registry data.**
- [ ] **Step 5: Run `pytest tests/test_capability_registry.py -q` and verify PASS.**
- [ ] **Step 6: Run the existing policy/tool-gateway tests to prove the new registry does not bypass policy.**
- [ ] **Step 7: Commit the validation layer and tests.**

### Task 3: Add platform-role mapping for Android, tablet, and PC

**Files:**
- Modify: `docs/capabilities/README.md`
- Create: `docs/capabilities/device-role-matrix.md`
- Inspect: `requirements-runtime-mobile.txt`
- Inspect: `runtime/project-nas.sh`
- Inspect: existing Android/Termux runtime documentation

**Interfaces:**
- Device roles are documentation-level routing metadata only.
- `ANDROID_EDGE`, `TABLET_EDGE`, `PC_BUILD`, `GITHUB_SOURCE`, and `NAS_RUNTIME` are the canonical role labels.

- [ ] **Step 1: Document Android as control/edge execution: Termux, relay/agent clients, lightweight scripts, status and approval.**
- [ ] **Step 2: Document PC as primary build/test/inference: repository checkout, pytest, Ollama, heavy model workloads, and artifact generation.**
- [ ] **Step 3: Document tablet as a secondary control/review surface rather than a second source of truth.**
- [ ] **Step 4: Document GitHub as source-of-truth synchronization boundary and NAS runtime as governed execution layer.**
- [ ] **Step 5: Add a failure/fallback table for device offline, GitHub unavailable, local model unavailable, and worker unavailable conditions.**
- [ ] **Step 6: Review documentation against the existing runtime certification and mobile requirements.**
- [ ] **Step 7: Commit the device-role documentation.**

### Task 4: Add a safe BOB-facing selection contract

**Files:**
- Create: `runtime/capability_selector.py`
- Create: `tests/test_capability_selector.py`
- Inspect: `runtime/orchestrator.py`
- Inspect: `runtime/cognitive_orchestrator.py`
- Inspect: `runtime/orchestration_policy.py`

**Interfaces:**
- `select_workers(records: list[dict], capability: str, platform_role: str | None = None) -> list[dict]` returns advisory worker/tool candidates ordered by deterministic preference.
- Selection must never return `PERSONAL`, `IGNORE`, or `REMOVE_CANDIDATE` records.
- Selection must never convert registry metadata into an executable permission.

- [ ] **Step 1: Write failing tests for worker selection, core-tool preference, personal/ignored exclusion, platform filtering, and deterministic ordering.**
- [ ] **Step 2: Run the focused selector tests and verify failure.**
- [ ] **Step 3: Implement selection as pure local logic over validated records.**
- [ ] **Step 4: Keep execution delegated to the existing ToolGateway/PolicyEngine; do not add direct subprocess, shell, filesystem, or network execution to the selector.**
- [ ] **Step 5: Run selector and policy tests and verify PASS.**
- [ ] **Step 6: Commit the selector and tests.**

### Task 5: Integrate documentation and status without changing the security boundary

**Files:**
- Modify: `ACTION-PLAN.md` only where verified status warrants it
- Modify: `Obsidian/03-Engineering/Action-Plan.md` only where the existing project workflow requires it
- Modify: `README.md` only to point to the capability matrix if the existing README structure supports it
- Create: `docs/capabilities/PROJECT-NAS-APP-ECOSYSTEM.md`

**Interfaces:**
- Documentation links to the canonical registry and device-role matrix.
- No new secrets, credentials, or external service configuration is added.

- [ ] **Step 1: Add a concise ecosystem map showing Android → BOB → NAS, PC build/inference, GitHub source control, and optional workers.**
- [ ] **Step 2: Record the core stack and the rule that app installation does not equal authorization.**
- [ ] **Step 3: Add the user-supplied app inventory as a reviewed snapshot with date `2026-08-20`.**
- [ ] **Step 4: Run documentation/link validation available in the repository.**
- [ ] **Step 5: Commit the ecosystem documentation.**

### Task 6: Full verification and handoff to PROJECT-BOB

**Files:**
- Inspect: existing `.github/workflows/` checks
- Inspect: `runtime/doctor.py`
- Inspect: `runtime/project-nas-certify.sh`
- Inspect: `ACTION-PLAN.md`

**Interfaces:**
- No new runtime authority is introduced.
- Capability registry remains advisory and fail-closed when malformed.

- [ ] **Step 1: Run the full pytest suite.**
- [ ] **Step 2: Run Python compilation/import checks and the existing doctor/certification checks.**
- [ ] **Step 3: Review the diff for secrets, permission escalation, hard-coded device paths, and policy bypasses.**
- [ ] **Step 4: Confirm GitHub Actions is green for the feature branch.**
- [ ] **Step 5: Open a draft pull request from `feat/project-nas-capability-matrix` to `main` with the verification evidence.**
- [ ] **Step 6: Do not merge until the local PC/Termux environment has consumed the branch and passed its platform-specific checks.**

## Rulings

- **Ruling:** Build the matrix as data plus a pure selector, not as app-specific runtime integrations. This keeps the architecture extensible and avoids coupling NAS to volatile Play Store applications.
- **Ruling:** Existing PolicyEngine/ToolGateway remain the execution authority. The matrix can recommend a worker but cannot grant access.
- **Ruling:** Keep the core small. External AI apps are useful as delegated workers, but the project must remain operational with local-first infrastructure.
- **Ruling:** Do not uninstall apps automatically. The matrix records `IGNORE`/`REMOVE_CANDIDATE`; physical device cleanup is a separate user-controlled operation.
