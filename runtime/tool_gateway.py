from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from typing import Any, Callable

from runtime.policy import Capability, PolicyEngine, RiskLevel, ToolRequest

MAX_MEMORY_LIMIT = 20
MAX_MEMORY_QUERY_CHARS = 500
MAX_MEMORY_TOTAL_CHARS = 6000
MAX_PROMPT_CHARS = 12000
MAX_PROMPT_RESPONSE_CHARS = 12000
MAX_PROGRESS_COMMITS = 50


@dataclass(frozen=True)
class ToolSpec:
    name: str
    capability: Capability
    risk: RiskLevel
    input_validator: Callable[[dict], dict]
    handler: Callable[[dict], Any]
    timeout_seconds: float = 5.0


class ToolGateway:
    """Registry and policy gate for bounded PROJECT-NAS tool execution."""

    ALLOWED_NAMESPACES = frozenset({"memory", "prompt", "status"})

    def __init__(self, policy: PolicyEngine | None = None, audit_limit: int = 100):
        if audit_limit < 1:
            raise ValueError("audit_limit must be positive")
        self.policy = policy or PolicyEngine()
        self._tools: dict[str, ToolSpec] = {}
        self.audit_log: list[dict[str, Any]] = []
        self._audit_limit = audit_limit

    def register(self, spec: ToolSpec) -> None:
        if not spec.name or spec.name in self._tools:
            raise ValueError("tool name must be unique and non-empty")
        if spec.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._tools[spec.name] = spec

    def execute(self, name: str, payload: dict) -> Any:
        namespace = name.split(".", 1)[0] if "." in name else ""
        if namespace not in self.ALLOWED_NAMESPACES:
            reason = f"tool namespace denied by default: {namespace or '<unknown>'}"
            self._record_audit(name, False, reason)
            raise PermissionError(reason)
        if name not in self._tools:
            reason = "unknown tool denied"
            self._record_audit(name, False, reason)
            raise KeyError(name)

        spec = self._tools[name]
        validated = spec.input_validator(payload)
        if not isinstance(validated, dict):
            raise ValueError("input validator must return an object")

        request = ToolRequest(
            tool_name=name,
            capability=spec.capability,
            risk=spec.risk,
            input=validated,
        )
        decision = self.policy.evaluate(request)
        self._record_audit(name, decision.allowed, decision.reason)
        if not decision.allowed:
            raise PermissionError(decision.reason)

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(spec.handler, validated)
        try:
            result = future.result(timeout=spec.timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            raise TimeoutError(f"tool timed out: {name}") from exc
        except Exception:
            executor.shutdown(wait=True)
            raise
        else:
            executor.shutdown(wait=True)
            return result

    def _record_audit(self, name: str, allowed: bool, reason: str) -> None:
        self.audit_log.append({"tool": name, "allowed": allowed, "reason": reason})
        if len(self.audit_log) > self._audit_limit:
            del self.audit_log[: len(self.audit_log) - self._audit_limit]


def _require_object(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    return payload


def _validate_empty(payload: dict) -> dict:
    payload = _require_object(payload)
    if payload:
        raise ValueError("unsupported arguments")
    return {}


def _validate_progress(payload: dict) -> dict:
    payload = _require_object(payload)
    if set(payload) - {"commits"}:
        raise ValueError("unsupported progress arguments")
    commits = payload.get("commits", 10)
    if not isinstance(commits, int) or isinstance(commits, bool) or not 1 <= commits <= MAX_PROGRESS_COMMITS:
        raise ValueError("commits must be an integer from 1 to 50")
    return {"commits": commits}


def _validate_memory(payload: dict) -> dict:
    payload = _require_object(payload)
    if set(payload) - {"query", "limit"}:
        raise ValueError("unsupported memory arguments")
    query = payload.get("query")
    if query is not None:
        if not isinstance(query, str):
            raise ValueError("query must be a string")
        if len(query) > MAX_MEMORY_QUERY_CHARS:
            raise ValueError("query exceeds maximum length of 500 characters")
        query = query.strip() or None
    limit = payload.get("limit", 5)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_MEMORY_LIMIT:
        raise ValueError("limit must be an integer from 1 to 20")
    return {"query": query, "limit": limit}


def _validate_prompt(payload: dict) -> dict:
    payload = _require_object(payload)
    if set(payload) - {"max_chars"}:
        raise ValueError("unsupported prompt arguments")
    max_chars = payload.get("max_chars", MAX_PROMPT_CHARS)
    if not isinstance(max_chars, int) or isinstance(max_chars, bool):
        raise ValueError("max_chars must be an integer")
    if not 1 <= max_chars <= MAX_PROMPT_RESPONSE_CHARS:
        raise ValueError("max_chars must be between 1 and 12000")
    return {"max_chars": max_chars}


def _bound_memory_result(result: Any) -> Any:
    """Enforce a gateway-level aggregate memory budget before context reaches callers."""
    if not isinstance(result, dict) or not isinstance(result.get("memories"), list):
        return result
    bounded = []
    used = 0
    for memory in result["memories"]:
        if not isinstance(memory, dict):
            continue
        document = str(memory.get("document", ""))
        remaining = MAX_MEMORY_TOTAL_CHARS - used
        if remaining <= 0:
            break
        clipped = document[:remaining]
        item = dict(memory)
        item["document"] = clipped
        bounded.append(item)
        used += len(clipped)
    return {**result, "memories": bounded, "count": len(bounded), "truncated": len(bounded) < len(result["memories"]) or used < sum(len(str(item.get("document", ""))) for item in result["memories"] if isinstance(item, dict))}


def build_default_gateway(progress_handler: Callable[[int], dict] | None = None) -> ToolGateway:
    """Create the bounded read-only v1 control plane."""
    if progress_handler is None:
        from runtime.backend import run_git_info
        progress_handler = run_git_info

    from runtime.backend import read_prompt, health_report
    from runtime.memory_injector import read_memories

    gateway = ToolGateway()
    gateway.register(ToolSpec(
        name="status.health",
        capability=Capability.READ_RUNTIME,
        risk=RiskLevel.LOW,
        input_validator=_validate_empty,
        handler=lambda payload: health_report(),
    ))
    gateway.register(ToolSpec(
        name="status.progress",
        capability=Capability.READ_REPOSITORY,
        risk=RiskLevel.LOW,
        input_validator=_validate_progress,
        handler=lambda payload: progress_handler(payload["commits"]),
    ))
    gateway.register(ToolSpec(
        name="prompt.get",
        capability=Capability.READ_RUNTIME,
        risk=RiskLevel.LOW,
        input_validator=_validate_prompt,
        handler=lambda payload: read_prompt(payload["max_chars"]),
    ))
    gateway.register(ToolSpec(
        name="memory.read",
        capability=Capability.READ_RUNTIME,
        risk=RiskLevel.LOW,
        input_validator=_validate_memory,
        handler=lambda payload: _bound_memory_result(read_memories(payload["query"], payload["limit"])),
    ))
    return gateway
