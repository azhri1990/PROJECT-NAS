import pytest

from runtime.cognitive_memory import CognitiveMemoryStore, MemoryLifecycle, MemoryProvenance


def test_user_approval_pins_memory_and_records_history(tmp_path):
    store = CognitiveMemoryStore(tmp_path / "memory.sqlite3")
    memory = store.add(
        "Nash prefers local-first systems",
        "PREFERENCE",
        MemoryProvenance("user", "session-1"),
        confidence=0.9,
        evidence=2,
    )

    pinned = store.approve_pinned(memory.id, approver="user")

    assert pinned.lifecycle == MemoryLifecycle.PINNED
    assert store.history(memory.id)
    assert store.history(memory.id)[-1]["approver"] == "user"


def test_rollback_restores_previous_lifecycle(tmp_path):
    store = CognitiveMemoryStore(tmp_path / "memory.sqlite3")
    memory = store.add(
        "SQLite is the local fallback",
        "FACT",
        MemoryProvenance("test", "rollback"),
        confidence=0.9,
        evidence=2,
    )
    store.promote_verified(memory.id, confidence=0.9, evidence=2)

    restored = store.rollback(memory.id)

    assert restored.lifecycle == MemoryLifecycle.NEW


def test_contradiction_detection_is_deterministic(tmp_path):
    store = CognitiveMemoryStore(tmp_path / "memory.sqlite3")
    store.add("Ollama is local", "FACT", MemoryProvenance("test", "positive"))
    store.add("Ollama is not local", "FACT", MemoryProvenance("test", "negative"))

    contradictions = store.find_contradictions("Ollama is not local", kind="FACT")

    assert len(contradictions) == 1
    assert contradictions[0].statement == "Ollama is local"


def test_consolidation_accumulates_one_new_observation(tmp_path):
    store = CognitiveMemoryStore(tmp_path / "memory.sqlite3")
    provenance = MemoryProvenance("test", "repeat")
    first = store.consolidate("SQLite is local", "FACT", provenance, confidence=0.8)
    second = store.consolidate("SQLite is local", "FACT", provenance, confidence=0.9)

    assert first.id == second.id
    assert second.evidence == 2
    assert second.confidence == 0.9


def test_review_reports_lifecycle_counts(tmp_path):
    store = CognitiveMemoryStore(tmp_path / "memory.sqlite3")
    store.add("A fact", "FACT", MemoryProvenance("test", "review"))
    report = store.review(decay=0.0)

    assert report["NEW"] == 1
    assert report["PINNED"] == 0


def test_invalid_approver_is_rejected(tmp_path):
    store = CognitiveMemoryStore(tmp_path / "memory.sqlite3")
    memory = store.add("A fact", "FACT", MemoryProvenance("test", "approval"))

    with pytest.raises(ValueError, match="approver"):
        store.approve_pinned(memory.id, approver="")
