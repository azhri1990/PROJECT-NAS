from pathlib import Path


def test_runtime_smoke_workflow_exercises_real_lifecycle():
    workflow = Path('.github/workflows/runtime-smoke.yml').read_text(encoding='utf-8')
    for command in (
        'runtime/project-nas.sh start',
        'runtime/project-nas.sh status',
        'runtime/project-nas.sh doctor',
        'runtime/project-nas.sh stop',
        'curl -fsS http://127.0.0.1:5001/health',
        'curl -fsS -X POST http://127.0.0.1:5001/chat',
    ):
        assert command in workflow


def test_runtime_certification_stays_loopback_and_zero_cost():
    workflow = Path('.github/workflows/runtime-smoke.yml').read_text(encoding='utf-8')
    assert '127.0.0.1' in workflow
    assert 'ollama' not in workflow.lower() or 'llama3.2:3b' in workflow
    assert 'pip install' in workflow
