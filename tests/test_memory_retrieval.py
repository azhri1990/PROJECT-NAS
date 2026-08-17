from runtime.memory_injector import SQLiteMemoryCollection


def test_sqlite_memory_retrieves_exact_match(tmp_path):
    memory = SQLiteMemoryCollection(str(tmp_path))

    memory.add([
        "PROJECT-NAS uses Ollama with llama3.2:3b locally."
    ])

    result = memory.query(["PROJECT-NAS uses Ollama"])

    documents = result["documents"][0]

    assert documents
    assert "llama3.2:3b" in documents[0]


def test_sqlite_memory_retrieves_related_query(tmp_path):
    memory = SQLiteMemoryCollection(str(tmp_path))

    memory.add([
        "PROJECT-NAS uses Ollama with llama3.2:3b locally.",
        "Nash works on PROJECT-NAS using Android and Termux.",
    ])

    result = memory.query(
        ["What local AI model does PROJECT-NAS use?"]
    )

    documents = result["documents"][0]

    assert documents
    assert "llama3.2:3b" in documents[0]


def test_sqlite_memory_filters_unrelated_query(tmp_path):
    memory = SQLiteMemoryCollection(str(tmp_path))

    memory.add([
        "PROJECT-NAS uses Ollama with llama3.2:3b locally.",
        "Nash works on PROJECT-NAS using Android and Termux.",
    ])

    result = memory.query(
        ["What is the weather today?"]
    )

    assert result["documents"][0] == []


def test_sqlite_memory_ranks_more_relevant_memory_first(tmp_path):
    memory = SQLiteMemoryCollection(str(tmp_path))

    memory.add([
        "Nash works on PROJECT-NAS using Android and Termux.",
        "PROJECT-NAS uses Ollama with llama3.2:3b locally.",
        "PROJECT-NAS has a SQLite memory fallback.",
    ])

    result = memory.query(
        ["Which local AI model does PROJECT-NAS use?"],
        n_results=3,
    )

    documents = result["documents"][0]

    assert documents
    assert "llama3.2:3b" in documents[0]

def test_tokens_accept_none():
    assert SQLiteMemoryCollection._tokens(None) == []


def test_tokens_use_conservative_normalization():
    tokens = SQLiteMemoryCollection._tokens(
        "models policies running deployed uses"
    )

    assert "model" in tokens
    assert "policy" in tokens
    assert "runn" in tokens
    assert "deploy" in tokens
    assert "uses" in tokens


def test_concept_expansion_links_ollama_and_ai():
    expanded = SQLiteMemoryCollection._expand_tokens(["ollama"])

    assert "ollama" in expanded
    assert "model" in expanded
    assert "ai" in expanded


def test_empty_query_returns_recent_memories(tmp_path):
    memory = SQLiteMemoryCollection(str(tmp_path))

    memory.add([
        "Older memory.",
        "Newer memory.",
    ])

    result = memory.query([""], n_results=2)

    assert result["documents"][0] == [
        "Newer memory.",
        "Older memory.",
    ]


def test_zero_result_limit_returns_empty(tmp_path):
    memory = SQLiteMemoryCollection(str(tmp_path))

    memory.add(["PROJECT-NAS uses Ollama locally."])

    result = memory.query(["Ollama"], n_results=0)

    assert result["documents"][0] == []
