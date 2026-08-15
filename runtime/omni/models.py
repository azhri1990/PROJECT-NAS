from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


class ProviderKind(str, Enum):
    OPENAI_COMPATIBLE = "openai_compatible"
    LOCAL_ONLY = "local_only"
    DEVICE_AGENT = "device_agent"


class ProviderStatus(str, Enum):
    SUPPORTED = "supported"
    OPTIONAL = "optional"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    kind: ProviderKind
    base_url: str
    api_key_env: str | None = None
    model: str = ""
    enabled: bool = True
    timeout_seconds: float = 15.0
    max_input_chars: int = 12000

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("provider name must not be blank")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("provider base_url must be an HTTP(S) URL")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_input_chars <= 0:
            raise ValueError("max_input_chars must be positive")
        if self.api_key_env is not None and not self.api_key_env.strip():
            raise ValueError("api_key_env must be non-blank when provided")


@dataclass(frozen=True)
class ProviderProfile:
    name: str
    display_name: str
    kind: ProviderKind
    status: ProviderStatus
    description: str
    default_base_url: str | None = None


@dataclass(frozen=True)
class ProviderHealth:
    name: str
    reachable: bool
    authenticated: bool | None
    latency_ms: float | None
    detail: str


@dataclass(frozen=True)
class ChatResult:
    text: str
    provider: str
    model: str
    latency_ms: float | None = None
