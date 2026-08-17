from pathlib import Path


def test_runtime_smoke_workflow_contains_operational_gates():
    workflow = Path('.github/workflows/runtime-smoke.yml').read_text(encoding='utf-8')
    required = (
        'runtime/project-nas.sh start',
        'runtime/project-nas.sh status',
        'runtime/project-nas.sh doctor',
        'runtime/project-nas.sh stop',
        'http://127.0.0.1:5001/health',
        'http://127.0.0.1:5001/chat',
    )
    assert all(item in workflow for item in required)


def test_runtime_smoke_uses_loopback_only_dependencies():
    workflow = Path('.github/workflows/runtime-smoke.yml').read_text(encoding='utf-8')
    assert "127.0.0.1" in workflow
    assert "PROJECT_NAS_OLLAMA_MODEL" in workflow
