import runtime.memory_injector as memory


def test_memory_read_recent_is_bounded_and_newest_first(tmp_path, monkeypatch):
    collection = memory.SQLiteMemoryCollection(str(tmp_path / "memory.sqlite3"))
    collection.add(
        ["old runtime memory", "middle runtime memory", "new runtime memory"],
        [{"source": "old"}, {"source": "middle"}, {"source": "new"}],
        ["mem-old", "mem-middle", "mem-new"],
    )
    monkeypatch.setattr(memory, "collection", collection)
    monkeypatch.setattr(memory, "MEMORY_BACKEND", "sqlite")
    result = memory.read_memories(limit=2)
    assert result["count"] == 2
    assert [item["id"] for item in result["memories"]] == ["mem-new", "mem-middle"]
    assert result["memories"][0]["metadata"] == {"source": "new"}


def test_memory_read_query_uses_existing_retrieval_and_empty_results(tmp_path, monkeypatch):
    collection = memory.SQLiteMemoryCollection(str(tmp_path / "memory.sqlite3"))
    collection.add(
        ["runtime controller is bounded", "coffee is unrelated", "runtime memory adapter"],
        [{"kind": "control"}, {"kind": "other"}, {"kind": "memory"}],
        ["mem-1", "mem-2", "mem-3"],
    )
    monkeypatch.setattr(memory, "collection", collection)
    monkeypatch.setattr(memory, "MEMORY_BACKEND", "sqlite")
    result = memory.read_memories(query="runtime", limit=5)
    assert result["count"] == 2
    assert all("runtime" in item["document"] for item in result["memories"])
    empty = memory.read_memories(query="nonexistent-term", limit=5)
    assert empty == {"memories": [], "count": 0}


def test_memory_read_metadata_is_safe_when_stored_metadata_is_invalid(tmp_path):
    collection = memory.SQLiteMemoryCollection(str(tmp_path / "memory.sqlite3"))
    collection.add(["test"], [{"valid": True}], ["mem-1"])
    with __import__("sqlite3").connect(collection.db_file) as conn:
        conn.execute("UPDATE memories SET metadata=? WHERE id=?", ("not-a-dict", "mem-1"))
    monkeypatch = __import__("pytest").MonkeyPatch()
    try:
        monkeypatch.setattr(memory, "collection", collection)
        monkeypatch.setattr(memory, "MEMORY_BACKEND", "sqlite")
        result = memory.read_memories(limit=1)
    finally:
        monkeypatch.undo()
    assert result["memories"][0]["metadata"] == {}
