import importlib.util
import sys


def load_module():
    spec = importlib.util.spec_from_file_location("memory_governance_test", "runtime/memory_injector.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_context_budget_is_deterministic(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_NAS_MEMORY_DB", str(tmp_path / "memory"))
    monkeypatch.setenv("PROJECT_NAS_TOTAL_PROMPT_CHARS", "200")
    module = load_module()
    module.MAX_TOTAL_PROMPT_CHARS = 200

    prompt, meta = module.build_context("S" * 200, "M" * 200, "hello")
    assert len(prompt) <= 200
    assert meta["budget_chars"] == 200
    assert meta["static_truncated"] is True
    assert meta["memory_truncated"] is True


def test_memory_redacts_common_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_NAS_MEMORY_DB", str(tmp_path / "memory"))
    module = load_module()
    raw = "api_key=super-secret-value Bearer abcdefghijklmnop sk-abcdefghijklmnopqrstuvwxyz"
    redacted = module.redact_memory_text(raw)
    assert "super-secret-value" not in redacted
    assert "abcdefghijklmnop" not in redacted
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in redacted
    assert "REDACTED" in redacted


def test_memory_retention_bounds_sqlite_backend(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_NAS_MEMORY_DB", str(tmp_path / "memory"))
    monkeypatch.setenv("PROJECT_NAS_MAX_PERSISTED_MEMORIES", "2")
    module = load_module()
    for index in range(4):
        module.collection.add(documents=[f"memory-{index}"], ids=[f"id-{index}"])
    result = module.read_memories(limit=20)
    assert result["count"] == 2
    assert [item["document"] for item in result["memories"]] == ["memory-3", "memory-2"]
