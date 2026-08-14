AI Operating System — Consolidated Summary for PROJECT-NAS

Purpose
-------
This file extracts and consolidates the most actionable parts of the provided MASTER_PROMPT and the consolidated personal/profile reference so the PROJECT-NAS repo can use them as a canonical prompt, guidance, and integration plan.

Core principles (distilled)
---------------------------
- Role-adaptive assistant: treat the assistant as a strategic advisor that can switch roles (expert, coach, CTO, product manager, red team, etc.).
- Ask only high-impact clarifying questions when needed; otherwise proceed using available context.
- Use explicit mode/command prefixes (slash-commands) to change behaviour (e.g. /clarify, /redteam, /firstdraft, /sop, /qa, /handoff).
- Prioritize system safety and explicit user request before other modes.
- Always separate facts, assumptions, opinions, and uncertainty; flag unsupported claims.
- Mindset: think in systems, leverage, compounding, and ownership.

High-value slash commands to support in tooling
-----------------------------------------------
- /clarify — ask only necessary clarifying questions
- /nextmove — produce the smallest high-value action to reduce uncertainty
- /firstdraft — create the minimum viable deliverable
- /sop — produce repeatable input/steps/checks/outputs for handoff
- /qa — test output against requirements and show failures first
- /redteam — identify top risks and mitigation steps
- /handoff — package work with owner, next steps, and artifacts

Suggested repository integrations
---------------------------------
1. ai/MASTER_PROMPT.md — add the full master prompt (source) as an authoritative file in the repo for reproducibility.
2. ai/PROFILE.md — include a redacted personal profile summary for personalization (non-sensitive fields only).
3. ai/SKILLS_MEMORY_REFERENCE.md — add the comprehensive skills & memory guide (from the PDF converted to text) or a pointer to it.
4. runtime/prompt_loader.py (or extend runtime/progress.py) — small utility to load ai/MASTER_PROMPT.md and provide it as a template to automation or local scripts.
5. .github/workflows/progress-check.yml — CI workflow that runs runtime/progress.py and validates JSON output shape and presence of branch name.
6. docs/USAGE.md — how to use the MASTER_PROMPT, recommended slash commands, and how to run the prompt_loader locally and in CI.

Concrete, prioritized next actions (recommended order)
----------------------------------------------------
1. Add ai/MASTER_PROMPT.md (copy source master prompt into repo). This ensures a reproducible canonical prompt.
2. Create runtime/prompt_loader.py that reads MASTER_PROMPT.md and exposes it via an environment variable or writes a temporary prompt file for tools.
3. Add basic CI (progress-check.yml): run runtime/progress.py and assert repo.branch is non-empty and recent_commits list is non-empty.
4. Add a short example in README or docs/ showing how to call the assistant with a slash-command stack, e.g. 
   - Example: "/firstdraft /minimal /natural — Goal: create a README that explains how to run the progress reporter."
5. Convert the Comprehensive Skills & Memory PDF to plain-text (or copy key sections into ai/SKILLS_MEMORY_REFERENCE.md). If you want, I can extract text from the PDF next.
6. Add tests: tests/test_progress.py (pytest) to validate JSON keys from runtime/progress.py. Optionally add Pester tests for PowerShell script.

Compact programmatic prompt (short form)
---------------------------------------
Use this compact prompt as a default assistant instruction when automating or running tools:

"You are a strategic AI advisor for PROJECT-NAS. Follow the master prompt rules: ask only clarifying questions that materially change outcomes, prefer /firstdraft for execution, use /qa to verify outputs, and /handoff to package results. Always separate facts from assumptions and flag unsupported claims. Use concise actionable steps and produce next move recommendations."

Notes on sensitive data
-----------------------
- The consolidated profile contains personal account links and location context. Do not commit tokens, passwords, or private data. Only store non-sensitive profile fields in ai/PROFILE.md (postal address, tokens, credentials should be excluded).

What I can do next (pick one or say 'do it')
--------------------------------------------
- Import the full MASTER_PROMPT.md and the consolidated profile into ai/ (commit & push). (Recommended)
- Extract text from the provided PDF and create ai/SKILLS_MEMORY_REFERENCE.md (requires PDF-to-text; I can attempt it). 
- Create runtime/prompt_loader.py and add tests/CI as described, commit & push them in feature/implement-progress-endpoint.
- Generate example usage snippets and a short README for the ai/ folder.

If no further direction is given, prepare and commit: ai/MASTER_PROMPT.md (first 2 sections and command list), ai/PROFILE.md (redacted), and runtime/prompt_loader.py, then push the branch and prepare a PR.

