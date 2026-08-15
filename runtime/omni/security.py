from __future__ import annotations

import ipaddress
from urllib.parse import urlparse


_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def is_allowed_provider_url(url: str, allowlist: set[str] | None = None) -> bool:
    """Allow only explicitly approved HTTP(S) hosts; loopback is allowed by default."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False

    host = parsed.hostname.lower().rstrip(".")
    allowed = {value.lower().rstrip(".") for value in (allowlist or set())}
    if host in _LOCAL_HOSTS:
        return True
    if host in allowed:
        return True

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False

    # Non-loopback private/link-local/reserved addresses require explicit allowlisting.
    return False


def redact_provider_metadata(metadata: dict[str, object]) -> dict[str, object]:
    """Return safe diagnostics with credential-like fields removed."""
    sensitive = {"api_key", "api_key_env", "authorization", "token", "password", "secret"}
    result: dict[str, object] = {}
    for key, value in metadata.items():
        if key.lower() in sensitive or "token" in key.lower() or "secret" in key.lower():
            result[key] = "[redacted]"
        else:
            result[key] = value
    return result


def classify_provider_action(action: str) -> str:
    if action in {"chat", "health"}:
        return action
    if action in {"device_control", "terminal", "filesystem_write", "destructive"}:
        return "device_control"
    return "unknown"
