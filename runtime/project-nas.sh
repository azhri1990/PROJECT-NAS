#!/bin/bash
# PROJECT-NAS local runtime controller + chat wrapper

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
MASTER_PROMPT_FILE="$PROJECT_ROOT/ai/MASTER_PROMPT.md"
CHAT_URL="${PROJECT_NAS_CHAT_URL:-http://127.0.0.1:5000/chat}"
OLLAMA_URL="${PROJECT_NAS_OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
PID_DIR="$PROJECT_ROOT/runtime/.pids"
LOG_DIR="$PROJECT_ROOT/runtime"
MEMORY_PID_FILE="$PID_DIR/memory-injector.pid"
OLLAMA_PID_FILE="$PID_DIR/ollama.pid"
MEMORY_LOG="$LOG_DIR/mobile-server.log"
OLLAMA_LOG="$LOG_DIR/ollama.log"

mkdir -p "$PID_DIR"

usage() {
    cat <<'EOF'
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

pid_is_running() {
    local pid_file="$1"
    [ -f "$pid_file" ] || return 1
    local pid
    pid=$(cat "$pid_file" 2>/dev/null || true)
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

write_pid() {
    printf '%s\n' "$1" > "$2"
}

wait_for_http() {
    local url="$1"
    local attempts="${2:-30}"
    for _ in $(seq 1 "$attempts"); do
        if curl -fsS --connect-timeout 1 --max-time 2 "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    return 1
}

start_ollama() {
    if curl -fsS --connect-timeout 1 --max-time 2 "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
        echo "✓ Ollama already available at $OLLAMA_URL"
        return 0
    fi

    if ! command -v ollama >/dev/null 2>&1; then
        echo "✗ Ollama executable not found." >&2
        return 1
    fi

    echo "Starting Ollama..."
    nohup ollama serve >>"$OLLAMA_LOG" 2>&1 &
    write_pid "$!" "$OLLAMA_PID_FILE"

    if ! wait_for_http "$OLLAMA_URL/api/tags" 30; then
        echo "✗ Ollama failed to become ready." >&2
        return 1
    fi
    echo "✓ Ollama ready"
}

start_memory() {
    if curl -fsS --connect-timeout 1 --max-time 2 "$CHAT_URL" >/dev/null 2>&1; then
        echo "✓ Memory injector already available at $CHAT_URL"
        return 0
    fi

    echo "Starting PROJECT-NAS memory injector..."
    nohup python "$PROJECT_ROOT/runtime/memory_injector.py" >>"$MEMORY_LOG" 2>&1 &
    write_pid "$!" "$MEMORY_PID_FILE"

    if ! wait_for_http "http://127.0.0.1:5000/health" 30; then
        echo "✗ Memory injector failed to become ready." >&2
        return 1
    fi
    echo "✓ Memory injector ready"
}

start_runtime() {
    start_ollama
    start_memory
    echo "PROJECT-NAS runtime: READY"
}

stop_one() {
    local name="$1"
    local pid_file="$2"
    if pid_is_running "$pid_file"; then
        local pid
        pid=$(cat "$pid_file")
        echo "Stopping $name (PID $pid)..."
        kill "$pid" 2>/dev/null || true
        for _ in $(seq 1 10); do
            kill -0 "$pid" 2>/dev/null || break
            sleep 1
        done
    fi
    rm -f "$pid_file"
}

stop_runtime() {
    stop_one "memory injector" "$MEMORY_PID_FILE"
    stop_one "Ollama" "$OLLAMA_PID_FILE"
    echo "PROJECT-NAS runtime: STOPPED"
}

status_runtime() {
    echo "=== PROJECT-NAS RUNTIME ==="
    if curl -fsS --connect-timeout 1 --max-time 2 "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
        echo "✓ Ollama      $OLLAMA_URL"
    else
        echo "✗ Ollama      unavailable"
    fi

    if curl -fsS --connect-timeout 1 --max-time 2 "http://127.0.0.1:5000/health" >/dev/null 2>&1; then
        echo "✓ Memory API  http://127.0.0.1:5000"
    else
        echo "✗ Memory API  unavailable"
    fi

    if pid_is_running "$MEMORY_PID_FILE"; then
        echo "✓ Controller  memory PID $(cat "$MEMORY_PID_FILE")"
    fi
    if pid_is_running "$OLLAMA_PID_FILE"; then
        echo "✓ Controller  Ollama PID $(cat "$OLLAMA_PID_FILE")"
    fi
}

doctor_runtime() {
    python "$PROJECT_ROOT/runtime/doctor.py"
}

chat_runtime() {
    for cmd in curl jq; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            echo "Error: '$cmd' is required but not installed." >&2
            exit 1
        fi
    done

    if [ ! -f "$MASTER_PROMPT_FILE" ]; then
        echo "Error: canonical prompt not found: $MASTER_PROMPT_FILE" >&2
        exit 1
    fi

    CONTEXT=$(cat "$MASTER_PROMPT_FILE")
    read -r -p "Enter your command or question: " USER_INPUT
    if [ -z "$USER_INPUT" ]; then
        echo "Error: no input given." >&2
        exit 1
    fi

    PAYLOAD=$(jq -n --arg context "$CONTEXT" --arg prompt "$USER_INPUT" \
      '{context: $context, prompt: $prompt}')

    if ! RESPONSE=$(curl --fail-with-body -sS --connect-timeout 5 --max-time 120 \
      -X POST "$CHAT_URL" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD"); then
        echo "Error: could not complete request to $CHAT_URL. Run 'runtime/project-nas.sh start'." >&2
        exit 1
    fi

    echo "$RESPONSE" | jq -r '.response // .error // "No response field returned."'
}

case "${1:-}" in
    start) start_runtime ;;
    stop) stop_runtime ;;
    restart) stop_runtime; start_runtime ;;
    status) status_runtime ;;
    doctor) doctor_runtime ;;
    chat) chat_runtime ;;
    -h|--help|help) usage ;;
    *) usage; exit 2 ;;
esac
