from pathlib import Path

import pytest

from runtime.autonomous_learning import AutonomousLearningLoop
from runtime.cognitive_memory import MemoryLifecycle, MemoryProvenance
from runtime.verified_learning import LearningType


def test_autonomous_learning_review_exposes_cognitive_lifecycle(tmp_path):
    loop = AutonomousLearningLoop(
        db_path=tmp_path / "learning.sqlite3",
        cognitive_db_path=tmp_path / "cognitive.sqlite3",
    )
    loop.learn(
        kind=LearningType.FACT,
        statement="SQLite is local",
        confidence=0.9,
        evidence=2,
        verified=True,
    )

    report = loop.review_memory(decay=0.0)

    assert report[MemoryLifecycle.TRUSTED.value] == 1


def test_unverified_learning_cannot_be_pinned(tmp_path):
    loop = AutonomousLearningLoop(
        db_path=tmp_path / "learning.sqlite3",
        cognitive_db_path=tmp_path / "cognitive.sqlite3",
    )
    loop.cognitive_memory.add(
        "Unverified claim",
        "FACT",
        MemoryProvenance("model", "generated-1"),
        confidence=0.9,
        evidence=2,
    )

    with pytest.raises(PermissionError, match="verified or trusted"):
        loop.approve_permanent("Unverified claim", approver="user")


def test_rollback_memory_delegates_to_cognitive_store(tmp_path):
    loop = AutonomousLearningLoop(
        db_path=tmp_path / "learning.sqlite3",
        cognitive_db_path=tmp_path / "cognitive.sqlite3",
    )
    loop.learn(
        kind=LearningType.FACT,
        statement="SQLite is local",
        confidence=0.9,
        evidence=2,
        verified=True,
    )
    cognitive = loop.recall_cognitive("SQLite local", 1)[0]

    restored = loop.rollback_memory(cognitive.id)

    assert restored.lifecycle == MemoryLifecycle.NEW
