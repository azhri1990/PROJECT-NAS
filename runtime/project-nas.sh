#!/bin/bash
# PROJECT-NAS local wrapper

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
MASTER_PROMPT_FILE="$PROJECT_ROOT/ai/MASTER_PROMPT.md"
CHAT_URL="${PROJECT_NAS_CHAT_URL:-http://127.0.0.1:5000/chat}"

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
    echo "Error: could not complete request to $CHAT_URL. Is memory_injector.py running?" >&2
    exit 1
fi

echo "$RESPONSE" | jq -r '.response // .error // "No response field returned."'
