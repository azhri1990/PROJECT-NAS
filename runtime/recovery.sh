#!/bin/bash
# PROJECT-NAS zero-cost, health-aware runtime recovery helper.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONTROLLER="$SCRIPT_DIR/project-nas.sh"
BACKEND_HEALTH_URL="${PROJECT_NAS_BACKEND_HEALTH_URL:-http://127.0.0.1:5001/health}"

if curl -fsS --connect-timeout 1 --max-time 2 "$BACKEND_HEALTH_URL" >/dev/null 2>&1; then
    echo "✓ Runtime healthy; no recovery required."
    exit 0
fi

echo "Runtime unhealthy; invoking existing controller start path..."
"$CONTROLLER" start

curl -fsS --connect-timeout 2 --max-time 5 "$BACKEND_HEALTH_URL" >/dev/null 2>&1
echo "✓ Runtime recovery verified."
