import runtime.memory_injector as memory_injector


def test_read_memories_bounds_total_context(monkeypatch):
    class FakeCollection:
        def read_records(self, query=None, limit=5):
            return [
                ("one", "A" * 3000, "{}"),
                ("two", "B" * 3000, "{}"),
                ("three", "C" * 3000, "{}"),
            ][:limit]

    monkeypatch.setattr(memory_injector, "MEMORY_BACKEND", "sqlite")
    monkeypatch.setattr(memory_injector, "collection", FakeCollection())
    monkeypatch.setattr(memory_injector, "MAX_MEMORY_CHARS", 3000)
    monkeypatch.setattr(memory_injector, "MAX_MEMORY_TOTAL_CHARS", 6000)

    result = memory_injector.read_memories(limit=20)

    assert result["count"] == 2
    assert sum(len(item["document"]) for item in result["memories"]) <= 6000


def test_read_memories_preserves_metadata_and_ids(monkeypatch):
    class FakeCollection:
        def read_records(self, query=None, limit=5):
            return [("id-1", "remember this", '{"source": "test"}')]

    monkeypatch.setattr(memory_injector, "MEMORY_BACKEND", "sqlite")
    monkeypatch.setattr(memory_injector, "collection", FakeCollection())

    result = memory_injector.read_memories(query="remember", limit=1)

    assert result == {
        "memories": [
            {"id": "id-1", "document": "remember this", "metadata": {"source": "test"}}
        ],
        "count": 1,
    }
