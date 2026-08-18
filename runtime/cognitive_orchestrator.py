"""Governed second-brain orchestration for PROJECT-NAS/JARVIS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from runtime.orchestration_verifier import VerificationResult, verify_result
from runtime.second_brain import SecondBrain
from runtime.orchestration_tools import ToolRegistry
from runtime.verified_learning import LearningDecision, LearningType


@dataclass(frozen=True)
class CognitiveOutcome:
    """Auditable result of one governed cognitive cycle."""

    tool_name: str
    memory: tuple[dict[str, Any], ...]
    result: Any
    verification: VerificationResult
    learning: LearningDecision | None


class BrainLike(Protocol):
    def recall(self, query: str, limit: int = 5) -> list[Any]: ...

    def learn(
        self,
        *,
        kind: LearningType,
        statement: str,
        confidence: float,
        evidence: int,
        verified: bool,
        source: str,
        context: str = "",
        contradiction: bool = False,
    ) -> LearningDecision: ...


class CognitiveOrchestrator:
    """Connect recall, governed execution, verification, and verified learning.

    The brain supplies context only. ToolRegistry remains authoritative for
    capability and policy decisions; verification remains fail-closed.
    """

    def __init__(
        self,
        *,
        brain: BrainLike | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.brain = brain or SecondBrain()
        self.registry = registry or ToolRegistry()

    def recall_context(self, query: str, limit: int = 5) -> tuple[dict[str, Any], ...]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("memory query must be a non-empty string")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
            raise ValueError("memory limit must be an integer from 1 to 20")

        memories = self.brain.recall(query.strip(), limit)
        context: list[dict[str, Any]] = []
        for memory in memories:
            context.append(
                {
                    "id": getattr(memory, "id", None),
                    "statement": getattr(memory, "statement", ""),
                    "kind": getattr(getattr(memory, "kind", None), "value", getattr(memory, "kind", None)),
                    "confidence": getattr(memory, "confidence", None),
                    "evidence": getattr(memory, "evidence", None),
                    "source": getattr(memory, "source", None),
                    "observed_at": getattr(memory, "observed_at", None),
                }
            )
        return tuple(context)

    def execute(
        self,
        *,
        tool_name: str,
        payload: dict[str, Any],
        memory_query: str | None = None,
        learn_statement: str | None = None,
        learn_kind: LearningType = LearningType.TASK,
        learn_confidence: float = 0.9,
        learn_evidence: int = 2,
    ) -> CognitiveOutcome:
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise ValueError("tool_name must be a non-empty string")
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        if memory_query is not None and (not isinstance(memory_query, str) or not memory_query.strip()):
            raise ValueError("memory_query must be non-empty when provided")
        if learn_statement is not None and (not isinstance(learn_statement, str) or not learn_statement.strip()):
            raise ValueError("learn_statement must be non-empty when provided")

        memory = self.recall_context(memory_query, 5) if memory_query else ()

        # Memory is context, never authority. The registry performs the actual
        # capability/policy decision before the tool handler can run.
        result = self.registry.execute(tool_name.strip(), payload)
        verification = verify_result(tool_name.strip(), result)

        learning: LearningDecision | None = None
        if learn_statement is not None:
            learning = self.brain.learn(
                kind=learn_kind,
                statement=learn_statement.strip(),
                confidence=learn_confidence,
                evidence=learn_evidence,
                verified=verification.ok,
                source=f"cognitive_orchestrator:{tool_name.strip()}",
                context=memory[0]["statement"] if memory else "",
            )

        return CognitiveOutcome(
            tool_name=tool_name.strip(),
            memory=memory,
            result=result,
            verification=verification,
            learning=learning,
        )
