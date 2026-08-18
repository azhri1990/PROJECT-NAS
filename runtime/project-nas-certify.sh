#!/bin/bash
# PROJECT-NAS zero-cost local certification wrapper.
# Uses the existing runtime controller and never assumes a green result.
set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CONTROLLER="$SCRIPT_DIR/project-nas.sh"
RECOVERY="$SCRIPT_DIR/recovery.sh"
RECOVERY_SELFTEST="$SCRIPT_DIR/recovery-selftest.sh"
HISTORY_FILE="${PROJECT_NAS_CERT_HISTORY_FILE:-$PROJECT_ROOT/runtime/certification-history.jsonl}"
HISTORY_MAX_BYTES="${PROJECT_NAS_CERTIFICATION_HISTORY_MAX_BYTES:-65536}"

fail() {
    echo "✗ $*" >&2
    echo "CERTIFICATION: RED"
    exit 1
}

show_history() {
    HISTORY_FILE="$HISTORY_FILE" HISTORY_MAX_BYTES="$HISTORY_MAX_BYTES" python - <<'PY'
import os
from runtime.certification_history import CertificationHistory

history = CertificationHistory(os.environ["HISTORY_FILE"], int(os.environ["HISTORY_MAX_BYTES"]))
records = history.records()
print("=== PROJECT-NAS CERTIFICATION HISTORY ===")
if not records:
    print("No certification history recorded.")
    raise SystemExit(0)
for record in records[-10:]:
    print(
        f"{record.get('timestamp', '?')} | {record.get('result', '?')} | "
        f"{record.get('commit', '?')} | tests={record.get('tests', '?')}"
    )
print("=========================================")
print(f"Latest: {history.latest().get('result', '?')}")
PY
}

case "${1:-}" in
    --history|history)
        show_history
        exit 0
        ;;
esac

command -v python >/dev/null 2>&1 || fail "Python executable not found."
command -v curl >/dev/null 2>&1 || fail "curl is required."
command -v git >/dev/null 2>&1 || fail "git is required."

GATE_STATUS_FILE="$(mktemp)"
REGRESSION_LOG="$(mktemp)"
cleanup() {
    rm -f "$GATE_STATUS_FILE" "$REGRESSION_LOG"
}
trap cleanup EXIT

record_history() {
    local result="$1" tests="$2"
    HISTORY_FILE="$HISTORY_FILE" HISTORY_MAX_BYTES="$HISTORY_MAX_BYTES" \
        RESULT="$result" TESTS="$tests" GATE_STATUS_FILE="$GATE_STATUS_FILE" \
        COMMIT="$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)" \
        TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        python - <<'PY'
import os
from runtime.certification_history import CertificationHistory

gates = {}
with open(os.environ["GATE_STATUS_FILE"], encoding="utf-8") as handle:
    for line in handle:
        name, status = line.rstrip("\n").split("\t", 1)
        gates[name] = status

CertificationHistory(
    os.environ["HISTORY_FILE"],
    int(os.environ["HISTORY_MAX_BYTES"]),
).record(
    timestamp=os.environ["TIMESTAMP"],
    commit=os.environ["COMMIT"],
    result=os.environ["RESULT"],
    tests=int(os.environ["TESTS"]),
    gates=gates,
)
PY
}

[ -f "$RECOVERY" ] || fail "Runtime recovery helper is missing."
[ -f "$RECOVERY_SELFTEST" ] || fail "Recovery self-test is missing."

if ! bash "$RECOVERY"; then
    fail "Runtime recovery failed."
fi

echo "=== PROJECT-NAS CERTIFICATION ==="

run_gate() {
    local name="$1"
    shift
    echo "→ $name"
    if "$@"; then
        printf '%s\tGREEN\n' "$name" >> "$GATE_STATUS_FILE"
        echo "✓ $name"
    else
        printf '%s\tRED\n' "$name" >> "$GATE_STATUS_FILE"
        echo "✗ $name" >&2
        record_history "RED" 0 || echo "⚠ Could not persist certification history." >&2
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
run_gate "Recovery helper syntax" bash -n "$RECOVERY"
run_gate "Recovery self-test syntax" bash -n "$RECOVERY_SELFTEST"
run_gate "Controlled recovery simulation" bash "$RECOVERY_SELFTEST"
run_gate "Repository integrity" git -C "$PROJECT_ROOT" diff --check

echo "→ Regression suite"
if python -m pytest -q tests | tee "$REGRESSION_LOG"; then
    printf '%s\tGREEN\n' "Regression suite" >> "$GATE_STATUS_FILE"
    TEST_COUNT="$(grep -Eo '[0-9]+ passed' "$REGRESSION_LOG" | tail -1 | awk '{print $1}')"
    TEST_COUNT="${TEST_COUNT:-0}"
    echo "✓ Regression suite"
else
    printf '%s\tRED\n' "Regression suite" >> "$GATE_STATUS_FILE"
    echo "✗ Regression suite" >&2
    record_history "RED" 0 || echo "⚠ Could not persist certification history." >&2
    echo "CERTIFICATION: RED"
    exit 1
fi

# The regression detector is part of the certification schema. It must be
# present in the current gate set before comparing with a baseline that already
# contains this gate; on a genuine regression it is changed to RED below.
printf '%s\tGREEN\n' "Regression detection" >> "$GATE_STATUS_FILE"

COMPARISON_OUTPUT="$(
    HISTORY_FILE="$HISTORY_FILE" HISTORY_MAX_BYTES="$HISTORY_MAX_BYTES" TEST_COUNT="$TEST_COUNT" GATE_STATUS_FILE="$GATE_STATUS_FILE" \
        python - <<'PY'
import os
from runtime.certification_history import CertificationHistory
from runtime.certification_regression import compare_certifications

history = CertificationHistory(os.environ["HISTORY_FILE"], int(os.environ["HISTORY_MAX_BYTES"]))
baseline = next((r for r in reversed(history.records()) if r.get("result") == "GREEN"), None)

gates = {}
with open(os.environ["GATE_STATUS_FILE"], encoding="utf-8") as handle:
    for line in handle:
        name, status = line.rstrip("\n").split("\t", 1)
        gates[name] = status

current = {"result": "GREEN", "tests": int(os.environ["TEST_COUNT"]), "gates": gates}
report = compare_certifications(baseline, current)
if report.regression:
    print("RED")
    for issue in report.issues:
        print(issue)
else:
    print("GREEN")
PY
)"

if [ "${COMPARISON_OUTPUT%%$'\n'*}" = "RED" ]; then
    sed -i '$d' "$GATE_STATUS_FILE"
    printf '%s\tRED\n' "Regression detection" >> "$GATE_STATUS_FILE"
    echo "✗ Regression detected" >&2
    echo "$COMPARISON_OUTPUT" | tail -n +2 >&2
    record_history "RED" "$TEST_COUNT" || echo "⚠ Could not persist certification history." >&2
    echo "CERTIFICATION: RED"
    exit 1
fi

record_history "GREEN" "$TEST_COUNT" || echo "⚠ Could not persist certification history." >&2

echo "========================================"
echo "CERTIFICATION: GREEN"
echo "========================================"
