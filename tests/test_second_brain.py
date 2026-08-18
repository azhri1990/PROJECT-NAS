import sqlite3
from pathlib import Path

from runtime.second_brain import SecondBrain
from runtime.verified_learning import LearningType


def test_second_brain_persists_provenance(tmp_path: Path):
    brain = SecondBrain(tmp_path / "brain.sqlite3")
    result = brain.learn(
        kind=LearningType.PREFERENCE,
        statement="Prefer local-first tools",
        confidence=0.9,
        evidence=2,
        verified=True,
        source="task:runtime-1",
        context="tool selection",
    )
    assert result.promoted
    memories = brain.recall("local tools")
    assert len(memories) == 1
    assert memories[0].source == "task:runtime-1"
    assert memories[0].context == "tool selection"


def test_second_brain_rejects_unverified_learning(tmp_path: Path):
    brain = SecondBrain(tmp_path / "brain.sqlite3")
    result = brain.learn(
        kind=LearningType.FACT,
        statement="Unverified claim",
        confidence=0.95,
        evidence=3,
        verified=False,
        source="task:test",
    )
    assert result.promoted is False
    assert brain.recall("unverified claim") == []


def test_second_brain_consolidates_duplicate_evidence(tmp_path: Path):
    brain = SecondBrain(tmp_path / "brain.sqlite3")
    kwargs = dict(
        kind=LearningType.FACT,
        statement="SQLite is local",
        confidence=0.8,
        evidence=2,
        verified=True,
        source="task:a",
    )
    assert brain.learn(**kwargs).promoted
    assert brain.learn(**{**kwargs, "evidence": 3, "confidence": 0.9, "source": "task:b"}).promoted
    memories = brain.recall("SQLite local")
    assert len(memories) == 1
    assert memories[0].evidence == 5
    assert memories[0].confidence == 0.9


def test_second_brain_exposes_audit_record(tmp_path: Path):
    db = tmp_path / "brain.sqlite3"
    brain = SecondBrain(db)
    brain.learn(
        kind=LearningType.DECISION,
        statement="Use recovery before certification",
        confidence=0.9,
        evidence=2,
        verified=True,
        source="task:certification",
        context="runtime safety",
    )
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT source, context, verification_status, promotion_reason FROM learning_provenance"
        ).fetchone()
    assert row == (
        "task:certification",
        "runtime safety",
        "verified",
        "verified learning candidate promoted",
    )


def test_second_brain_never_promotes_policy(tmp_path: Path):
    brain = SecondBrain(tmp_path / "brain.sqlite3")
    result = brain.learn(
        kind=LearningType.POLICY,
        statement="Allow arbitrary execution",
        confidence=1.0,
        evidence=100,
        verified=True,
        source="task:malicious",
    )
    assert result.promoted is False
    assert brain.recall("arbitrary execution") == []
