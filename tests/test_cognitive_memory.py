from runtime.autonomous_learning import AutonomousLearningLoop
from runtime.cognitive_memory import (
    CognitiveMemoryStore,
    MemoryLifecycle,
    MemoryProvenance,
)
from runtime.verified_learning import LearningType


def test_provenance_is_required_and_deterministic(tmp_path):
    store = CognitiveMemoryStore(tmp_path / "memory.sqlite3")
    provenance = MemoryProvenance(source="user", reference="session-1")
    memory = store.add(statement="Nash prefers local-first systems", kind="PREFERENCE", provenance=provenance)
    again = store.add(statement="Nash prefers local-first systems", kind="PREFERENCE", provenance=provenance)
    assert memory.id == again.id
    assert memory.provenance == provenance
    assert again.evidence == 0


def test_repeated_evidence_accumulates_only_on_existing_memory(tmp_path):
    store = CognitiveMemoryStore(tmp_path / "memory.sqlite3")
    provenance = MemoryProvenance("test", "repeat")
    store.add("SQLite is local", "FACT", provenance, confidence=0.8, evidence=2)
    memory = store.add("SQLite is local", "FACT", provenance, confidence=0.7, evidence=1)
    assert memory.evidence == 3
    assert memory.confidence == 0.8


def test_verified_memory_progresses_to_trusted(tmp_path):
    store = CognitiveMemoryStore(tmp_path / "memory.sqlite3")
    memory = store.add("Use SQLite as the local memory fallback", "SYSTEM_STATE", MemoryProvenance("test", "case-1"))
    assert memory.lifecycle == MemoryLifecycle.NEW
    memory = store.promote_verified(memory.id, confidence=0.9, evidence=2)
    assert memory.lifecycle == MemoryLifecycle.TRUSTED


def test_low_support_memory_stays_verified_not_trusted(tmp_path):
    store = CognitiveMemoryStore(tmp_path / "memory.sqlite3")
    memory = store.add("A weak observation", "EVENT", MemoryProvenance("test", "weak"))
    memory = store.promote_verified(memory.id, confidence=0.8, evidence=1)
    assert memory.lifecycle == MemoryLifecycle.VERIFIED


def test_contradictory_evidence_marks_memory_conflicted(tmp_path):
    store = CognitiveMemoryStore(tmp_path / "memory.sqlite3")
    memory = store.add("The runtime is local", "FACT", MemoryProvenance("test", "case-2"))
    memory = store.promote_verified(memory.id, confidence=0.9, evidence=2)
    conflicted = store.mark_conflicted(memory.id, MemoryProvenance("test", "case-3"))
    assert conflicted.lifecycle == MemoryLifecycle.CONFLICTED


def test_policy_cannot_become_trusted_automatically(tmp_path):
    store = CognitiveMemoryStore(tmp_path / "memory.sqlite3")
    memory = store.add("Grant shell capability", "POLICY", MemoryProvenance("model", "generated-1"))
    assert store.promote_verified(memory.id, confidence=1.0, evidence=100).lifecycle != MemoryLifecycle.TRUSTED


def test_recall_ranks_relevant_confident_fresh_memory(tmp_path):
    store = CognitiveMemoryStore(tmp_path / "memory.sqlite3")
    store.add("SQLite is the memory backend", "SYSTEM_STATE", MemoryProvenance("test", "1"), confidence=0.9, evidence=5)
    store.add("Ollama is local", "SYSTEM_STATE", MemoryProvenance("test", "2"), confidence=0.5, evidence=1)
    results = store.recall("SQLite memory", limit=1)
    assert len(results) == 1
    assert results[0].statement == "SQLite is the memory backend"


def test_revalidation_can_mark_trusted_memory_stale(tmp_path):
    store = CognitiveMemoryStore(tmp_path / "memory.sqlite3")
    memory = store.add("A trusted fact", "FACT", MemoryProvenance("test", "stale"))
    memory = store.promote_verified(memory.id, confidence=0.8, evidence=5)
    assert memory.lifecycle == MemoryLifecycle.TRUSTED
    assert store.revalidate(decay=0.4) == 1
    assert store.recall("trusted fact")[0].lifecycle == MemoryLifecycle.STALE


def test_autonomous_learning_populates_cognitive_memory(tmp_path):
    loop = AutonomousLearningLoop(db_path=tmp_path / "learning.sqlite3", cognitive_db_path=tmp_path / "cognitive.sqlite3")
    decision = loop.learn(kind=LearningType.FACT, statement="SQLite is the durable local fallback", confidence=0.9, evidence=2, verified=True)
    assert decision.promoted
    memories = loop.recall_cognitive("SQLite durable fallback")
    assert memories
    assert memories[0].lifecycle == MemoryLifecycle.TRUSTED
    assert memories[0].provenance.source == "autonomous_learning"
