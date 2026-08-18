import tempfile
from pathlib import Path

from runtime.autonomous_learning import AutonomousLearningLoop
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
