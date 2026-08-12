#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "AGENTS.md",
    "PROJECT-NAS.md",
    "README.md",
    "CONTRIBUTING.md",
    "project.json",
    "docs/architecture/README.md",
    "docs/standards/README.md",
    "docs/governance/README.md",
    "docs/validation/README.md",
    "security/README.md",
    "knowledge/README.md",
    "skills/README.md",
    "operations/README.md",
]

errors = []

for item in REQUIRED:
    if not (ROOT / item).is_file():
        errors.append(f"Missing required file: {item}")

try:
    json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
except Exception as exc:
    errors.append(f"Invalid project.json: {exc}")

secret_patterns = [
    r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"gh[pousr]_[A-Za-z0-9_]{20,}",
    r"sk-[A-Za-z0-9]{20,}",
]

for path in ROOT.rglob("*"):
    if not path.is_file() or ".git" in path.parts:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    for pattern in secret_patterns:
        if re.search(pattern, text):
            errors.append(f"Possible secret pattern in: {path.relative_to(ROOT)}")

if errors:
    print("VALIDATION FAILED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("VALIDATION PASSED")
