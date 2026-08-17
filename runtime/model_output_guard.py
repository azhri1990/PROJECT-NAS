"""Deterministic validation and bounding for local model responses."""

from __future__ import annotations

MAX_MODEL_RESPONSE_CHARS = 16000


def guard_model_response(payload: object, *, max_chars: int = MAX_MODEL_RESPONSE_CHARS) -> dict:
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or not 1 <= max_chars <= MAX_MODEL_RESPONSE_CHARS:
        raise ValueError(f"max_chars must be an integer from 1 to {MAX_MODEL_RESPONSE_CHARS}")
    if not isinstance(payload, dict):
        raise ValueError("Ollama returned a non-object response")
    response = payload.get("response")
    if not isinstance(response, str) or not response.strip():
        raise ValueError("Ollama response field is missing or empty")
    if len(response) <= max_chars:
        return payload
    bounded = dict(payload)
    bounded["response"] = response[:max_chars]
    bounded["response_truncated"] = True
    return bounded
