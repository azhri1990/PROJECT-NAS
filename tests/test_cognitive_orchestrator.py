import pytest

from runtime.cognitive_orchestrator import CognitiveOrchestrator
from runtime.orchestration_policy import Capability
from runtime.orchestration_tools import ToolRegistry, ToolSpec
from runtime.verified_learning import LearningDecision, LearningType


class Memory:
    def __init__(self, statement):
        self.id = 1
        self.statement = statement
        self.kind = LearningType.FACT
        self.confidence = 0.9
        self.evidence = 3
        self.source = "test"
        self.observed_at = "now"


class Brain:
    def __init__(self):
        self.recall_calls = []
        self.learn_calls = []

    def recall(self, query, limit=5):
        self.recall_calls.append((query, limit))
        return [Memory("remembered context")]

    def learn(self, **kwargs):
        self.learn_calls.append(kwargs)
        return LearningDecision(True, "verified learning candidate promoted")


def health_registry():
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="status.health",
            capability=Capability.READ_RUNTIME,
            risk="low",
            input_schema={"type": "object", "additionalProperties": False},
            handler=lambda payload: {"status": "healthy"},
        )
    )
    return registry


def test_cycle_recall_execute_verify_and_learn():
    brain = Brain()
    orchestrator = CognitiveOrchestrator(brain=brain, registry=health_registry())

    outcome = orchestrator.execute(
        tool_name="status.health",
        payload={},
        memory_query="runtime health",
        learn_statement="The local runtime was healthy after the check.",
        learn_kind=LearningType.SYSTEM_STATE,
    )

    assert outcome.verification.ok is True
    assert outcome.memory[0]["statement"] == "remembered context"
    assert outcome.learning is not None
    assert brain.recall_calls == [("runtime health", 5)]
    assert brain.learn_calls[0]["verified"] is True
    assert brain.learn_calls[0]["source"] == "cognitive_orchestrator:status.health"


def test_brain_context_cannot_bypass_tool_policy():
    brain = Brain()
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="shell.exec",
            capability=Capability.EXECUTE_SAFE,
            risk="low",
            input_schema={"type": "object", "additionalProperties": False},
            handler=lambda payload: {"status": "should not run"},
        )
    )
    orchestrator = CognitiveOrchestrator(brain=brain, registry=registry)

    with pytest.raises(PermissionError):
        orchestrator.execute(
            tool_name="shell.exec",
            payload={},
            memory_query="use shell",
        )


def test_unknown_verification_contract_fails_closed_and_is_not_learned_as_verified():
    brain = Brain()
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="test.tool",
            capability=Capability.READ_RUNTIME,
            risk="low",
            input_schema={"type": "object", "additionalProperties": False},
            handler=lambda payload: {"ok": True},
        )
    )
    orchestrator = CognitiveOrchestrator(brain=brain, registry=registry)

    outcome = orchestrator.execute(
        tool_name="test.tool",
        payload={},
        learn_statement="This tool is trustworthy.",
    )

    assert outcome.verification.ok is False
    assert outcome.learning is not None
    assert brain.learn_calls[0]["verified"] is False


def test_memory_query_validation_is_bounded():
    orchestrator = CognitiveOrchestrator(brain=Brain(), registry=health_registry())
    with pytest.raises(ValueError):
        orchestrator.recall_context("runtime", 21)
    with pytest.raises(ValueError):
        orchestrator.recall_context("", 5)
