#!/bin/bash
# PROJECT-NAS zero-cost, health-aware runtime recovery helper.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONTROLLER="${PROJECT_NAS_RECOVERY_CONTROLLER:-$SCRIPT_DIR/project-nas.sh}"
BACKEND_HEALTH_URL="${PROJECT_NAS_BACKEND_HEALTH_URL:-http://127.0.0.1:5001/health}"
MEMORY_HEALTH_URL="${PROJECT_NAS_MEMORY_HEALTH_URL:-http://127.0.0.1:5000/health}"
OLLAMA_HEALTH_URL="${PROJECT_NAS_OLLAMA_BASE_URL:-http://127.0.0.1:11434}/api/tags"

runtime_healthy() {
    curl -fsS --connect-timeout 1 --max-time 2 "$BACKEND_HEALTH_URL" >/dev/null 2>&1 && \
    curl -fsS --connect-timeout 1 --max-time 2 "$MEMORY_HEALTH_URL" >/dev/null 2>&1 && \
    curl -fsS --connect-timeout 1 --max-time 2 "$OLLAMA_HEALTH_URL" >/dev/null 2>&1
}

if runtime_healthy; then
    echo "✓ Runtime healthy; no recovery required."
    exit 0
fi

echo "Runtime unhealthy; invoking existing controller start path..."
"$CONTROLLER" start

runtime_healthy
echo "✓ Runtime recovery verified."
