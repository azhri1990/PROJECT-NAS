import importlib.util
import sys


BACKEND_PATH = "runtime/backend.py"


def load_backend():
    spec = importlib.util.spec_from_file_location("project_nas_backend", BACKEND_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_session_db_is_configurable(tmp_path, monkeypatch):
    db_path = tmp_path / "session.db"
    monkeypatch.setenv("PROJECT_NAS_SESSION_DB", str(db_path))

    backend = load_backend()

    assert backend.resolve_session_db() == str(db_path)


def test_plugin_name_must_be_a_simple_filename(tmp_path):
    backend = load_backend()
    backend.PLUGIN_DIR = str(tmp_path)

    assert backend.validate_plugin_name("safe_plugin") == "safe_plugin"

    for name in ("../escape", "..\\escape", "/absolute", "a/b", "a\\b"):
        try:
            backend.validate_plugin_name(name)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe plugin name accepted: {name}")
