# PROJECT-NAS — Mobile → PC Transfer Manifest

Generated: 2026-08-13

## Purpose
Portable transfer package containing the PROJECT-NAS material recovered from the user's mobile-era work and persistent file library.

## Included source artifacts
- `ai/MASTER_PROMPT.md` — primary AI operating system, commands, mindset, prompt engineering, learning, research, quality control and writing rules.
- `ai/Nash_Consolidated_AI_Operating_System_and_Profile.md` — consolidated operating system/profile/skills/marketing reference.
- `profile/comprehensive_profile.md` — profile and connection reference.
- `ai/comprehensive_skills_memory_reference.pdf` — skills and memory/data reference.
- `runtime/project-nas.sh` — PROJECT-NAS local wrapper.
- `runtime/memory_injector.py` — Flask + ChromaDB + Ollama local memory injector.

## Known architecture/runtime facts
- Wrapper targets `http://localhost:5000/chat`.
- Memory injector uses ChromaDB persistent storage in `claude-mem-db` beside the script.
- Local LLM endpoint is `http://localhost:11434/api/generate`.
- Recorded model name is `gemma4`.
- Wrapper expects `curl` and `jq`.

## Important gap
The original `Advertising AI Image Prompts - Product Shots & Marketing.mht` source was referenced by the consolidated document, but a separate raw MHT file was not recovered in the current library search. The consolidated document contains extracted source material from it.

## Repository status
This package is a transfer/archive package. It does NOT claim that all files are already present in the GitHub repository. Repository inspection must happen separately.

## Privacy
This package intentionally excludes unrelated personal chat archives and third-party conversation exports. “Everything” here means everything identified as relevant to the PROJECT-NAS/personal-OS transfer, not every unrelated file in the persistent library.
