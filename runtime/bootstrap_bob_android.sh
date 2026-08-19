#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_ROOT="${PROJECT_NAS_ROOT:-$HOME/PROJECT-NAS}"
PYTHON_BIN="${PYTHON_BIN:-python}"

command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "Python is required in Termux" >&2; exit 1; }
[ -d "$REPO_ROOT" ] || { echo "PROJECT-NAS checkout not found: $REPO_ROOT" >&2; exit 1; }

cd "$REPO_ROOT"
"$PYTHON_BIN" -m runtime.doctor >/dev/null
printf '%s\n' "PROJECT-BOB Android worker prerequisites are ready."
printf '%s\n' "Set PROJECT_BOB_AUTH_TOKEN outside the repository before starting the worker."
