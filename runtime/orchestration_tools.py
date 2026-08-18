"""Explicit, schema-aware tool registry for JARVIS orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from runtime.orchestration_policy import Capability, Decision, PolicyEngine


@dataclass(frozen=True)
class ToolSpec:
    name: str
    capability: Capability
    risk: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]
    timeout_seconds: float = 5.0
    version: str = "1"
    verification: str | None = None


class ToolRegistry:
    """Allowlist registry. The model can select a name, never a capability."""

    def __init__(self, policy: PolicyEngine | None = None, audit_limit: int = 100) -> None:
        if audit_limit < 1:
            raise ValueError("audit_limit must be positive")
        self.policy = policy or PolicyEngine()
        self._tools: dict[str, ToolSpec] = {}
        self.audit: list[dict[str, Any]] = []
        self.audit_limit = audit_limit

    def register(self, spec: ToolSpec) -> None:
        if not spec.name or spec.name in self._tools:
            raise ValueError("tool name must be unique and non-empty")
        if spec.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not isinstance(spec.input_schema, dict):
            raise ValueError("input_schema must be an object")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    def execute(self, name: str, payload: dict[str, Any]) -> Any:
        spec = self.get(name)
        validated = self._validate(payload, spec.input_schema)
        decision = self.policy.evaluate(
            tool_name=spec.name,
            capability=spec.capability,
            risk=spec.risk,
            payload=validated,
        )
        self._audit(spec, decision, validated)
        if decision.decision != Decision.ALLOW:
            raise PermissionError(decision.reason)
        return spec.handler(validated)

    @staticmethod
    def _validate(payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        if schema.get("type") not in (None, "object"):
            raise ValueError("unsupported input schema type")
        if schema.get("additionalProperties") is False:
            properties = schema.get("properties", {})
            unknown = set(payload) - set(properties)
            if unknown:
                raise ValueError(f"unsupported arguments: {sorted(unknown)}")
        required = schema.get("required", [])
        missing = [key for key in required if key not in payload]
        if missing:
            raise ValueError(f"missing required arguments: {missing}")
        return dict(payload)

    def _audit(self, spec: ToolSpec, decision: Any, payload: dict[str, Any]) -> None:
        event = {
            "tool": spec.name,
            "version": spec.version,
            "capability": spec.capability.value,
            "risk": spec.risk,
            "decision": decision.decision.value,
            "reason": decision.reason,
            "arguments_keys": sorted(payload),
        }
        self.audit.append(event)
        if len(self.audit) > self.audit_limit:
            del self.audit[: len(self.audit) - self.audit_limit]
