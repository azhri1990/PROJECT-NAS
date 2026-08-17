import importlib.util
import sys
from pathlib import Path

DOCTOR_PATH = Path(__file__).resolve().parents[1] / "runtime" / "doctor.py"


def load_doctor():
    spec = importlib.util.spec_from_file_location("project_nas_doctor", DOCTOR_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_doctor_repository_is_independent_of_cwd(monkeypatch, tmp_path):
    doctor = load_doctor()
    monkeypatch.chdir(tmp_path)
    result = doctor.check_repository()
    assert result.ok


def test_doctor_database_uses_configured_path(monkeypatch, tmp_path):
    doctor = load_doctor()
    db_path = tmp_path / "nas" / "session.db"
    monkeypatch.setenv("PROJECT_NAS_SESSION_DB", str(db_path))
    result = doctor.check_database()
    assert result.ok
    assert db_path.exists()


def test_doctor_reports_unreachable_ollama_without_crashing(monkeypatch):
    doctor = load_doctor()
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:1/api/tags")
    result = doctor.check_ollama()
    assert not result.ok
    assert "unreachable" in result.detail


def test_doctor_offline_mode_skips_local_llm_probe(monkeypatch):
    doctor = load_doctor()
    monkeypatch.setenv("PROJECT_NAS_DOCTOR_OFFLINE", "1")
    result = doctor.check_ollama()
    assert result.ok
    assert "offline verification mode" in result.detail


def test_doctor_accepts_sqlite_memory_fallback(monkeypatch):
    doctor = load_doctor()
    monkeypatch.setattr(doctor.importlib.util, "find_spec", lambda name: None if name == "chromadb" else object())
    result = doctor.check_memory_backend()
    assert result.ok
    assert "SQLite fallback" in result.detail


def test_doctor_accepts_chromadb_when_available(monkeypatch):
    doctor = load_doctor()
    monkeypatch.setattr(doctor.importlib.util, "find_spec", lambda name: object() if name == "chromadb" else None)
    result = doctor.check_memory_backend()
    assert result.ok
    assert result.detail == "ChromaDB available"


def test_doctor_skips_sqlite_store_requirement_when_chromadb_is_active(monkeypatch, tmp_path):
    doctor = load_doctor()
    monkeypatch.setattr(doctor.importlib.util, "find_spec", lambda name: object() if name == "chromadb" else None)
    monkeypatch.setenv("PROJECT_NAS_MEMORY_DB", str(tmp_path / "missing"))
    result = doctor.check_memory_database()
    assert result.ok
    assert "ChromaDB store active" in result.detail
