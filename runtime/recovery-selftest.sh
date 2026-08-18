#!/bin/bash
# PROJECT-NAS zero-cost controlled recovery simulation.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

STATE_FILE="$TMP_DIR/state"
printf 'down\n' > "$STATE_FILE"

cat > "$TMP_DIR/curl" <<'EOF'
#!/bin/bash
set -euo pipefail
STATE_FILE="${PROJECT_NAS_RECOVERY_SELFTEST_STATE:?}"
if [[ "$(cat "$STATE_FILE")" == "up" ]]; then
    exit 0
fi
exit 22
EOF

cat > "$TMP_DIR/controller" <<'EOF'
#!/bin/bash
set -euo pipefail
STATE_FILE="${PROJECT_NAS_RECOVERY_SELFTEST_STATE:?}"
[[ "${1:-}" == "start" ]] || exit 2
printf 'up\n' > "$STATE_FILE"
EOF
chmod +x "$TMP_DIR/curl" "$TMP_DIR/controller"

export PATH="$TMP_DIR:$PATH"
export PROJECT_NAS_RECOVERY_SELFTEST_STATE="$STATE_FILE"
export PROJECT_NAS_RECOVERY_CONTROLLER="$TMP_DIR/controller"
export PROJECT_NAS_BACKEND_HEALTH_URL="http://selftest/backend"
export PROJECT_NAS_MEMORY_HEALTH_URL="http://selftest/memory"
export PROJECT_NAS_OLLAMA_BASE_URL="http://selftest/ollama"

output="$(bash "$SCRIPT_DIR/recovery.sh")"
grep -q "Runtime unhealthy; invoking existing controller start path" <<<"$output"
grep -q "Runtime recovery verified" <<<"$output"
[[ "$(cat "$STATE_FILE")" == "up" ]]

echo "✓ Controlled recovery simulation passed."
