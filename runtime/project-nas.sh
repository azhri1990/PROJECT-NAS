#!/bin/bash
# PROJECT-NAS local runtime controller + chat wrapper
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
MASTER_PROMPT_FILE="$PROJECT_ROOT/ai/MASTER_PROMPT.md"
CHAT_URL="${PROJECT_NAS_CHAT_URL:-http://127.0.0.1:5000/chat}"
OLLAMA_URL="${PROJECT_NAS_OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
PID_DIR="${PROJECT_NAS_TEST_PID_DIR:-$PROJECT_ROOT/runtime/.pids}"
LOG_DIR="$PROJECT_ROOT/runtime"
MEMORY_PID_FILE="$PID_DIR/memory-injector.pid"
MEMORY_ID_FILE="$PID_DIR/memory-injector.identity"
OLLAMA_PID_FILE="$PID_DIR/ollama.pid"
OLLAMA_ID_FILE="$PID_DIR/ollama.identity"
MEMORY_LOG="$LOG_DIR/mobile-server.log"
OLLAMA_LOG="$LOG_DIR/ollama.log"
mkdir -p "$PID_DIR"
usage() { cat <<'EOF'
Usage: runtime/project-nas.sh <command>

Commands:
  start     Start Ollama and the PROJECT-NAS memory injector
  stop      Stop PROJECT-NAS services started by this controller
  restart   Stop, then start the local runtime
  status    Show service and endpoint status
  doctor    Run PROJECT-NAS health diagnostics
  chat      Send a prompt through the local runtime
EOF
}
pid_is_running() { local pid_file="$1"; [ -f "$pid_file" ] || return 1; local pid; pid=$(cat "$pid_file" 2>/dev/null || true); [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; }
process_cmdline() { local pid="$1"; if [ -r "/proc/$pid/cmdline" ]; then tr '\0' ' ' < "/proc/$pid/cmdline" | sed 's/[[:space:]]*$//'; fi; }
process_identity_matches() { local pid_file="$1" identity_file="$2"; [ -f "$pid_file" ] || return 1; [ -f "$identity_file" ] || return 1; local pid expected actual; pid=$(cat "$pid_file" 2>/dev/null || true); expected=$(cat "$identity_file" 2>/dev/null || true); [[ "$pid" =~ ^[0-9]+$ ]] || return 1; [ -n "$expected" ] || return 1; kill -0 "$pid" 2>/dev/null || return 1; actual=$(process_cmdline "$pid"); [ -n "$actual" ] || return 1; [ "$actual" = "$expected" ]; }
write_pid() { printf '%s\n' "$1" > "$2"; }
write_identity() { local pid="$1" identity_file="$2" identity; identity=$(process_cmdline "$pid"); [ -n "$identity" ] || return 1; printf '%s\n' "$identity" > "$identity_file"; }
wait_for_http() { local url="$1" attempts="${2:-30}"; for _ in $(seq 1 "$attempts"); do if curl -fsS --connect-timeout 1 --max-time 2 "$url" >/dev/null 2>&1; then return 0; fi; sleep 1; done; return 1; }
start_ollama() { if curl -fsS --connect-timeout 1 --max-time 2 "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then echo "✓ Ollama already available at $OLLAMA_URL"; return 0; fi; if ! command -v ollama >/dev/null 2>&1; then echo "✗ Ollama executable not found." >&2; return 1; fi; echo "Starting Ollama..."; nohup ollama serve >>"$OLLAMA_LOG" 2>&1 & write_pid "$!" "$OLLAMA_PID_FILE"; if ! write_identity "$!" "$OLLAMA_ID_FILE"; then echo "✗ Could not establish Ollama process identity." >&2; rm -f "$OLLAMA_PID_FILE" "$OLLAMA_ID_FILE"; return 1; fi; if ! wait_for_http "$OLLAMA_URL/api/tags" 30; then echo "✗ Ollama failed to become ready." >&2; return 1; fi; echo "✓ Ollama ready"; }
start_memory() { if curl -fsS --connect-timeout 1 --max-time 2 "$CHAT_URL" >/dev/null 2>&1; then echo "✓ Memory injector already available at $CHAT_URL"; return 0; fi; echo "Starting PROJECT-NAS memory injector..."; nohup python "$PROJECT_ROOT/runtime/memory_injector.py" >>"$MEMORY_LOG" 2>&1 & write_pid "$!" "$MEMORY_PID_FILE"; if ! write_identity "$!" "$MEMORY_ID_FILE"; then echo "✗ Could not establish memory injector process identity." >&2; rm -f "$MEMORY_PID_FILE" "$MEMORY_ID_FILE"; return 1; fi; if ! wait_for_http "http://127.0.0.1:5000/health" 30; then echo "✗ Memory injector failed to become ready." >&2; return 1; fi; echo "✓ Memory injector ready"; }
start_runtime() { start_ollama; start_memory; echo "PROJECT-NAS runtime: READY"; }
stop_one() { local name="$1" pid_file="$2" identity_file="$3"; if ! [ -f "$pid_file" ] || ! [ -f "$identity_file" ]; then echo "✗ Cannot stop $name: controller ownership state is incomplete." >&2; return 1; fi; if ! process_identity_matches "$pid_file" "$identity_file"; then echo "✗ Cannot stop $name: process identity does not match controller ownership." >&2; return 1; fi; local pid; pid=$(cat "$pid_file"); echo "Stopping $name (PID $pid)..."; kill "$pid" 2>/dev/null || true; for _ in $(seq 1 10); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done; if kill -0 "$pid" 2>/dev/null; then echo "✗ $name did not terminate cleanly." >&2; return 1; fi; rm -f "$pid_file" "$identity_file"; }
stop_runtime() { local failed=0; if [ -f "$MEMORY_PID_FILE" ] || [ -f "$MEMORY_ID_FILE" ]; then stop_one "memory injector" "$MEMORY_PID_FILE" "$MEMORY_ID_FILE" || failed=1; elif curl -fsS --connect-timeout 1 --max-time 2 "http://127.0.0.1:5000/health" >/dev/null 2>&1; then echo "↷ Memory injector left running: externally managed." >&2; failed=1; else echo "↷ Memory injector externally managed/unavailable." >&2; failed=1; fi; if [ -f "$OLLAMA_PID_FILE" ] || [ -f "$OLLAMA_ID_FILE" ]; then stop_one "Ollama" "$OLLAMA_PID_FILE" "$OLLAMA_ID_FILE" || failed=1; elif curl -fsS --connect-timeout 1 --max-time 2 "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then echo "↷ Ollama left running: externally managed." >&2; failed=1; else echo "↷ Ollama externally managed/unavailable." >&2; failed=1; fi; if [ "$failed" -ne 0 ]; then echo "PROJECT-NAS runtime: STOPPED WITH ERRORS" >&2; return 1; fi; echo "PROJECT-NAS runtime: STOPPED"; }
status_runtime() { echo "=== PROJECT-NAS RUNTIME ==="; if curl -fsS --connect-timeout 1 --max-time 2 "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then echo "✓ Ollama      $OLLAMA_URL"; else echo "✗ Ollama      unavailable"; fi; if curl -fsS --connect-timeout 1 --max-time 2 "http://127.0.0.1:5000/health" >/dev/null 2>&1; then echo "✓ Memory API  http://127.0.0.1:5000"; else echo "✗ Memory API  unavailable"; fi; if process_identity_matches "$MEMORY_PID_FILE" "$MEMORY_ID_FILE"; then echo "✓ Controller  memory PID $(cat "$MEMORY_PID_FILE")"; fi; if process_identity_matches "$OLLAMA_PID_FILE" "$OLLAMA_ID_FILE"; then echo "✓ Controller  Ollama PID $(cat "$OLLAMA_PID_FILE")"; fi; }
doctor_runtime() { python "$PROJECT_ROOT/runtime/doctor.py"; }
chat_runtime() { for cmd in curl jq; do if ! command -v "$cmd" >/dev/null 2>&1; then echo "Error: '$cmd' is required but not installed." >&2; exit 1; fi; done; if [ ! -f "$MASTER_PROMPT_FILE" ]; then echo "Error: canonical prompt not found: $MASTER_PROMPT_FILE" >&2; exit 1; fi; CONTEXT=$(cat "$MASTER_PROMPT_FILE"); read -r -p "Enter your command or question: " USER_INPUT; if [ -z "$USER_INPUT" ]; then echo "Error: no input given." >&2; exit 1; fi; PAYLOAD=$(jq -n --arg context "$CONTEXT" --arg prompt "$USER_INPUT" '{context: $context, prompt: $prompt}'); if ! RESPONSE=$(curl --fail-with-body -sS --connect-timeout 5 --max-time 120 -X POST "$CHAT_URL" -H "Content-Type: application/json" -d "$PAYLOAD"); then echo "Error: could not complete request to $CHAT_URL. Run 'runtime/project-nas.sh start'." >&2; exit 1; fi; echo "$RESPONSE" | jq -r '.response // .error // "No response field returned."'; }
case "${1:-}" in start) start_runtime ;; stop) stop_runtime ;; restart) stop_runtime; start_runtime ;; status) status_runtime ;; doctor) doctor_runtime ;; chat) chat_runtime ;; -h|--help|help) usage ;; *) usage; exit 2 ;; esac
