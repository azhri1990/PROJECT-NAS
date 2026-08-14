Action plan for progress-update-query

Goal
----
Provide a reliable way to extract and report project progress (session todos + repository state) so automation and reviewers can see current work and resume it.

Scope & Deliverables
--------------------
1. runtime/progress.py (added) — CLI that outputs JSON with branch, recent commits, working-tree status, and optional session todos from a provided SQLite DB.
2. runtime/progress.ps1 (added) — PowerShell fallback for Windows environments without Python.
3. Documentation: ACTION-PLAN.md (this file) describing how to run and extend the tool.
4. Tests: add basic tests that validate JSON output shape for both scripts (can be run with pytest or PowerShell Pester later).
5. CI: add a minimal CI job that runs the progress reporter and verifies it returns a non-empty branch name and recent commits when run in the repo.

Implementation steps (concrete)
------------------------------
1. Verify current scripts (runtime/progress.py and runtime/progress.ps1) — run locally to ensure Python or PowerShell path works.
2. Add tests:
   - Python: add tests/test_progress.py that runs runtime/progress.py via subprocess and asserts JSON keys (repo.branch, repo.recent_commits).
   - PowerShell: optional Pester tests or skip on CI if Windows runner is not used.
3. Add CI workflow:
   - Create .github/workflows/progress-check.yml that uses ubuntu-latest to run Python and execute runtime/progress.py and assert output.
4. Improve session integration:
   - Add optional API endpoint or CLI flag to load the Copilot session DB path by default from environment or configured location.
   - Provide a small wrapper to upload/export the todos export artifact to a central place or attach to a PR.
5. Review & merge:
   - Open PR for feature/implement-progress-endpoint (already pushed).
   - Address any review feedback, then merge to main.

Next immediate actions (this branch)
-----------------------------------
- Commit and push this ACTION-PLAN.md to feature/implement-progress-endpoint (done by the assistant).
- Mark the session todo 'create-action-plan' done and record the plan in the session DB.

Notes
-----
- No dependencies were added. The Python script works if Python is available; PowerShell fallback supports Windows.
- Tests and CI are not yet added; if you want, I can add the CI workflow and tests in this branch ready for review.

"Let's proceed to add tests and CI" is a recommended next step.
