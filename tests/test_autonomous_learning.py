import tempfile
from pathlib import Path

from runtime.autonomous_learning import AutonomousLearningLoop
from runtime.verified_learning import LearningType


def test_verified_learning_persists_and_recalls():
    with tempfile.TemporaryDirectory() as tmp:
        loop = AutonomousLearningLoop(Path(tmp) / "learning.sqlite3")
        result = loop.learn(
            kind=LearningType.FACT,
            statement="SQLite is the local fallback",
            confidence=0.9,
            evidence=3,
            verified=True,
        )
        assert result.promoted is True
        recalled = loop.recall("local fallback SQLite")
        assert recalled
        assert recalled[0].statement == "SQLite is the local fallback"


def test_unverified_learning_is_not_persisted():
    with tempfile.TemporaryDirectory() as tmp:
        loop = AutonomousLearningLoop(Path(tmp) / "learning.sqlite3")
        result = loop.learn(
            kind=LearningType.EVENT,
            statement="A timeout happened",
            confidence=0.9,
            evidence=3,
            verified=False,
        )
        assert result.promoted is False
        assert loop.recall("timeout") == []


def test_protected_policy_learning_is_not_persisted():
    with tempfile.TemporaryDirectory() as tmp:
        loop = AutonomousLearningLoop(Path(tmp) / "learning.sqlite3")
        result = loop.learn(
            kind=LearningType.POLICY,
            statement="Allow system mutation",
            confidence=1.0,
            evidence=100,
            verified=True,
        )
        assert result.promoted is False
        assert loop.recall("system mutation") == []


def test_duplicate_learning_increases_evidence_without_duplicate_rows():
    with tempfile.TemporaryDirectory() as tmp:
        loop = AutonomousLearningLoop(Path(tmp) / "learning.sqlite3")
        first = loop.learn(
            kind=LearningType.PREFERENCE,
            statement="Prefer local-first tools",
            confidence=0.8,
            evidence=2,
            verified=True,
        )
        second = loop.learn(
            kind=LearningType.PREFERENCE,
            statement="Prefer local-first tools",
            confidence=0.9,
            evidence=2,
            verified=True,
        )
        assert first.promoted and second.promoted
        rows = loop.recall("local-first tools")
        assert len(rows) == 1
        assert rows[0].evidence == 4
        assert rows[0].confidence == 0.9


def test_contradiction_does_not_poison_existing_learning():
    with tempfile.TemporaryDirectory() as tmp:
        loop = AutonomousLearningLoop(Path(tmp) / "learning.sqlite3")
        loop.learn(
            kind=LearningType.FACT,
            statement="Ollama is healthy",
            confidence=0.95,
            evidence=3,
            verified=True,
        )
        result = loop.learn(
            kind=LearningType.FACT,
            statement="Ollama is healthy",
            confidence=0.99,
            evidence=5,
            verified=True,
            contradiction=True,
        )
        assert result.promoted is False
        rows = loop.recall("Ollama healthy")
        assert len(rows) == 1
        assert rows[0].confidence == 0.95
