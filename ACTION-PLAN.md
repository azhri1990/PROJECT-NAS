Action plan for progress-update-query

Goal
----
Provide a reliable way to extract and report project progress (session todos + repository state) so automation and reviewers can see current work and resume it.

Scope & Deliverables
--------------------
1. runtime/progress.py — CLI that outputs JSON with branch, recent commits, working-tree status, and optional session todos from a provided SQLite DB.
2. runtime/progress.ps1 — PowerShell fallback for Windows environments without Python.
3. Documentation: ACTION-PLAN.md — this file describes how to run and extend the tool.
4. Tests: tests/test_progress.py — validates JSON output shape and SQLite todo loading.
5. CI: .github/workflows/progress-check.yml — compiles Python sources, runs the progress tests, and verifies the reporter returns a branch value and recent commits.

Completed
---------
- Progress reporter and PowerShell fallback are present.
- Feature branch `feature/implement-progress-endpoint` was merged into `main` as PR #1.
- Added progress reporter tests.
- Added a minimal dependency-free CI workflow for the progress subsystem.
- Removed the generated Conda workflow because the repository has no `environment.yml` and the workflow could not provide a valid build.

Next actions
------------
1. Confirm the new GitHub Actions run completes successfully.
2. If CI passes, keep this workflow as the baseline CI gate for progress/runtime changes.
3. Extend coverage to the FastAPI backend once its runtime dependency strategy is formalized.
4. Add session integration through an environment/configured SQLite path rather than a machine-specific absolute path.

Notes
-----
- The progress reporter itself uses only Python standard-library modules and Git.
- The CI job installs only pytest; the runtime reporter has no third-party dependency requirement.
- The local AI/memory stack remains separate from the dependency-free progress CI path.

"Let's proceed to add tests and CI" is now implemented; verification is the remaining immediate gate.
