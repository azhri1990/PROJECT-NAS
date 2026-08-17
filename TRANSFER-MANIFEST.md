# PROJECT-NAS — Mobile → PC Transfer Manifest

Generated: 2026-08-13  
Status: historical transfer record; current runtime configuration is authoritative over this archive.

## Purpose
Portable transfer package containing PROJECT-NAS material recovered from the user's mobile-era work and persistent project files.

## Included source artifacts
- `ai/MASTER_PROMPT.md` — primary AI operating system and operating rules.
- `ai/Nash_Consolidated_AI_Operating_System_and_Profile.md` — consolidated operating-system/profile reference.
- `profile/comprehensive_profile.md` — project profile reference.
- `runtime/project-nas.sh` — local runtime controller.
- `runtime/memory_injector.py` — Flask + local memory/LLM bridge.

## Current runtime contract
- Memory API: `http://127.0.0.1:5000`
- Chat endpoint: `/chat`
- Memory health endpoint: `/health`
- Ollama API: `http://127.0.0.1:11434/api/generate`
- Default local model: `llama3.2:3b`
- Memory storage: `runtime/claude-mem-db` by default, configurable with `PROJECT_NAS_MEMORY_DB`
- Session storage: repository-local `session.db` by default, configurable with `PROJECT_NAS_SESSION_DB`
- Wrapper dependencies: `curl`, `jq`, Python runtime dependencies

## Control-plane contract
The runtime now uses a bounded, read-only tool gateway for control-plane operations. Default tools are limited to health, repository progress, canonical prompt retrieval, and bounded memory reads. Process execution, network access, and repository writes remain denied by default by policy.

## Historical gap
The original `Advertising AI Image Prompts - Product Shots & Marketing.mht` source was referenced by older consolidated material, but the separate raw MHT file was not recovered during the original transfer search. This manifest records that historical gap; it does not imply the file is required for the runtime.

## Repository status
This file is a historical transfer record. The executable runtime, tests, CI configuration, and current project documentation are authoritative for present behavior.

## Privacy
This package intentionally excludes unrelated personal chat archives and third-party conversation exports. “Everything” in this manifest means everything identified as relevant to the PROJECT-NAS/personal-OS transfer, not every unrelated file in persistent storage.
