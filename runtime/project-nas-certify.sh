#!/bin/bash
# PROJECT-NAS zero-cost local certification wrapper.
# Uses the existing runtime controller and never assumes a green result.
set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CONTROLLER="$SCRIPT_DIR/project-nas.sh"

fail() {
    echo "✗ $*" >&2
    echo "CERTIFICATION: RED"
    exit 1
}

command -v python >/dev/null 2>&1 || fail "Python executable not found."
command -v curl >/dev/null 2>&1 || fail "curl is required."
command -v git >/dev/null 2>&1 || fail "git is required."

started_by_certify=0

if curl -fsS --connect-timeout 1 --max-time 2 "${PROJECT_NAS_BACKEND_HEALTH_URL:-http://127.0.0.1:5001/health}" >/dev/null 2>&1; then
    echo "✓ Runtime already healthy; preserving external ownership."
else
    echo "Runtime unavailable; starting under controller ownership..."
    "$CONTROLLER" start || fail "Runtime failed to start."
    started_by_certify=1
fi

cleanup() {
    if [ "$started_by_certify" -eq 1 ]; then
        "$CONTROLLER" stop >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

echo "=== PROJECT-NAS CERTIFICATION ==="

run_gate() {
    local name="$1"
    shift
    echo "→ $name"
    if "$@"; then
        echo "✓ $name"
    else
        echo "✗ $name" >&2
        echo "CERTIFICATION: RED"
        exit 1
    fi
}

run_gate "Doctor" python "$PROJECT_ROOT/runtime/doctor.py"
run_gate "Backend health" curl -fsS --connect-timeout 2 --max-time 5 "${PROJECT_NAS_BACKEND_HEALTH_URL:-http://127.0.0.1:5001/health}"
run_gate "Memory health" curl -fsS --connect-timeout 2 --max-time 5 "${PROJECT_NAS_MEMORY_HEALTH_URL:-http://127.0.0.1:5000/health}"
run_gate "Ollama health" curl -fsS --connect-timeout 2 --max-time 5 "${PROJECT_NAS_OLLAMA_BASE_URL:-http://127.0.0.1:11434}/api/tags"
run_gate "Python compilation" python -m compileall -q runtime tests
run_gate "Shell syntax" bash -n "$CONTROLLER"
run_gate "Repository integrity" git -C "$PROJECT_ROOT" diff --check
run_gate "Regression suite" python -m pytest -q tests

echo "========================================"
echo "CERTIFICATION: GREEN"
echo "========================================"
