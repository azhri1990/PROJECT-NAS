import importlib.util
import os
import sys


def load_module():
    spec = importlib.util.spec_from_file_location("prompt_loader", "runtime/prompt_loader.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_prompt_loader_resolves_paths_from_repository_root(monkeypatch, tmp_path):
    module = load_module()
    monkeypatch.chdir(tmp_path)
    text, path = module.load_prompt()
    assert text
    assert path.endswith(os.path.join("ai", "MASTER_PROMPT.md"))
