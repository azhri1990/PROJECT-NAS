"""Deterministic classification of local model transport failures."""

from __future__ import annotations

import requests


def classify_model_failure(exc: BaseException) -> str:
    if isinstance(exc, requests.Timeout):
        return "timeout"
    if isinstance(exc, requests.ConnectionError):
        return "unavailable"
    if isinstance(exc, requests.HTTPError):
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in {400, 404}:
            return "model_unavailable"
        return "http_error"
    return "invalid_response"
