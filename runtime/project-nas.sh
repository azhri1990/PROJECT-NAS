#!/bin/bash
# PROJECT-NAS Universal Wrapper

set -uo pipefail

MASTER_PROMPT_FILE="./CLAUDE.md"
CHAT_URL="http://localhost:5000/chat"

# Fail early and clearly if required tools are missing
for cmd in curl jq; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "Error: '$cmd' is required but not installed." >&2
        exit 1
    fi
done

echo "Loading PROJECT-NAS OS Context..."
if [ -f "$MASTER_PROMPT_FILE" ]; then
    CONTEXT=$(cat "$MASTER_PROMPT_FILE")
else
    echo "Warning: CLAUDE.md not found. Run ./setup.sh first."
    exit 1
fi

echo "Enter your command or question:"
read -r USER_INPUT

if [ -z "$USER_INPUT" ]; then
    echo "Error: no input given."
    exit 1
fi

# Build JSON safely with jq instead of raw string interpolation.
# This is what fixes the broken-JSON bug on quotes/apostrophes.
# Context and prompt are sent as separate fields so the server can
# tell "background info" apart from "the actual question."
PAYLOAD=$(jq -n --arg context "$CONTEXT" --arg prompt "$USER_INPUT" \
  '{context: $context, prompt: $prompt}')

if ! RESPONSE=$(curl -s -X POST "$CHAT_URL" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"); then
    echo "Error: could not reach $CHAT_URL. Is memory_injector.py running?" >&2
    exit 1
fi

echo "$RESPONSE" | jq -r '.response // .error // "No response field returned."'
