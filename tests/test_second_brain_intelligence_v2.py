import tempfile
from pathlib import Path

import pytest

from runtime.autonomous_learning import AutonomousLearningLoop
from runtime.cognitive_memory import MemoryLifecycle, MemoryProvenance
from runtime.second_brain import SecondBrain
from runtime.verified_learning import LearningType


def test_memory_recall_prefers_relevant_high_confidence_evidence():
    with tempfile.TemporaryDirectory() as tmp:
        loop = AutonomousLearningLoop(Path(tmp) / "learning.sqlite3")
        loop.learn(kind=LearningType.FACT, statement="SQLite is the local fallback", confidence=0.8, evidence=2, verified=True)
        loop.learn(kind=LearningType.FACT, statement="SQLite is the local fallback for memory", confidence=0.95, evidence=5, verified=True)
        recalled = loop.recall("local fallback memory")
        assert recalled[0].statement.endswith("for memory")


def test_contradictory_statement_is_rejected_against_existing_memory():
    with tempfile.TemporaryDirectory() as tmp:
        loop = AutonomousLearningLoop(Path(tmp) / "learning.sqlite3")
        loop.learn(kind=LearningType.FACT, statement="Ollama is healthy", confidence=0.95, evidence=4, verified=True)
        result = loop.learn(kind=LearningType.FACT, statement="Ollama is not healthy", confidence=0.95, evidence=4, verified=True)
        assert result.promoted is False
        assert "contradiction" in result.reason.lower()


def test_memory_confidence_decays_without_new_evidence():
    with tempfile.TemporaryDirectory() as tmp:
        loop = AutonomousLearningLoop(Path(tmp) / "learning.sqlite3")
        loop.learn(kind=LearningType.FACT, statement="A stable fact", confidence=0.9, evidence=3, verified=True)
        changed = loop.revalidate(decay=0.1)
        assert changed == 1
        recalled = loop.recall("stable fact")
        assert recalled[0].confidence == 0.8


def test_repeated_verified_learning_consolidates_into_one_memory():
    with tempfile.TemporaryDirectory() as tmp:
        loop = AutonomousLearningLoop(Path(tmp) / "learning.sqlite3")
        loop.learn(kind=LearningType.FACT, statement="Local-first is preferred", confidence=0.8, evidence=2, verified=True)
        loop.learn(kind=LearningType.FACT, statement="Local-first is preferred", confidence=0.9, evidence=3, verified=True)
        consolidated = loop.consolidate("local-first")
        assert consolidated == 1
        recalled = loop.recall("local-first preferred")
        assert recalled[0].evidence == 5


def test_second_brain_detects_knowledge_gaps():
    with tempfile.TemporaryDirectory() as tmp:
        brain = SecondBrain(Path(tmp) / "brain.sqlite3")
        brain.learn(
            kind=LearningType.FACT,
            statement="SQLite is the durable local fallback",
            confidence=0.9,
            evidence=2,
            verified=True,
            source="test",
        )
        gaps = brain.knowledge_gaps(["SQLite local fallback", "Kubernetes deployment architecture"])
        assert gaps == ["Kubernetes deployment architecture"]


def test_second_brain_can_pin_verified_memory():
    with tempfile.TemporaryDirectory() as tmp:
        brain = SecondBrain(Path(tmp) / "brain.sqlite3")
        brain.learn(
            kind=LearningType.FACT,
            statement="SQLite is the durable local fallback",
            confidence=0.9,
            evidence=2,
            verified=True,
            source="test",
        )
        memory = brain.recall("SQLite durable fallback", 1)[0]
        pinned = brain.approve_permanent(memory.id, approver="Nash")
        assert pinned.lifecycle == MemoryLifecycle.PINNED


def test_second_brain_exposes_history_and_rollback():
    with tempfile.TemporaryDirectory() as tmp:
        brain = SecondBrain(Path(tmp) / "brain.sqlite3")
        brain.learn(
            kind=LearningType.FACT,
            statement="SQLite is the durable local fallback",
            confidence=0.9,
            evidence=2,
            verified=True,
            source="test",
        )
        memory = brain.learning.cognitive_memory.recall("SQLite durable fallback", 1)[0]
        assert brain.memory_history(memory.id)
        restored = brain.rollback_memory(memory.id)
        assert restored.lifecycle == MemoryLifecycle.NEW


def test_second_brain_rejects_unverified_permanent_promotion():
    with tempfile.TemporaryDirectory() as tmp:
        brain = SecondBrain(Path(tmp) / "brain.sqlite3")
        brain.learning.cognitive_memory.add(
            "Unverified claim",
            "FACT",
            MemoryProvenance("model", "generated-1"),
            confidence=0.9,
            evidence=2,
        )
        cognitive = brain.learning.cognitive_memory.recall("Unverified claim", 1)[0]
        with pytest.raises(PermissionError, match="verified or trusted"):
            brain.approve_permanent(cognitive.id, approver="Nash")
