from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
import json
from typing import Any, Callable

from runtime.policy import Capability, PolicyEngine, RiskLevel, ToolRequest


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
        if name not in self._tools:
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
            executor.shutdown(wait=False, cancel_futures=True)
            raise
        else:
            executor.shutdown(wait=True, cancel_futures=True)

        try:
            json.dumps(result)
        except (TypeError, ValueError) as exc:
            raise ValueError("tool result must be JSON-serializable") from exc
        return result

    def _record_audit(self, name: str, allowed: bool, reason: str) -> None:
        self.audit_log.append({"tool": name, "allowed": allowed, "reason": reason})
        if len(self.audit_log) > self._audit_limit:
            del self.audit_log[: len(self.audit_log) - self._audit_limit]


def _validate_progress(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    if set(payload) - {"commits"}:
        raise ValueError("unsupported progress arguments")
    commits = payload.get("commits", 10)
    if not isinstance(commits, int) or isinstance(commits, bool) or not 1 <= commits <= 50:
        raise ValueError("commits must be an integer from 1 to 50")
    return {"commits": commits}


def build_default_gateway(progress_handler: Callable[[int], dict] | None = None) -> ToolGateway:
    """Create the v1 gateway with only the bounded repository-progress read tool."""
    if progress_handler is None:
        from runtime.backend import run_git_info

        progress_handler = run_git_info

    gateway = ToolGateway()
    gateway.register(
        ToolSpec(
            name="repo.progress",
            capability=Capability.READ_REPOSITORY,
            risk=RiskLevel.LOW,
            input_validator=_validate_progress,
            handler=lambda payload: progress_handler(payload["commits"]),
        )
    )
    return gateway
