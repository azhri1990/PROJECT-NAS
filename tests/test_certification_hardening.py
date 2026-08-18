from runtime.certification_history import CertificationHistory
from runtime.certification_regression import compare_certifications


def test_history_never_exceeds_bound_when_single_record_is_oversized(tmp_path):
    path = tmp_path / "history.jsonl"
    history = CertificationHistory(path, max_bytes=256)
    history.record(
        timestamp="2026-08-18T00:00:00Z",
        commit="a" * 40,
        result="GREEN",
        tests=150,
        gates={"x" * 500: "GREEN"},
    )
    assert path.stat().st_size <= 256


def test_regression_detects_missing_current_gate(tmp_path):
    baseline = {
        "result": "GREEN",
        "tests": 150,
        "gates": {"Doctor": "GREEN", "Ollama health": "GREEN"},
    }
    current = {
        "result": "GREEN",
        "tests": 150,
        "gates": {"Doctor": "GREEN"},
    }
    report = compare_certifications(baseline, current)
    assert report.regression
    assert "Gate missing: Ollama health" in report.issues


def test_regression_rejects_invalid_baseline_test_count():
    baseline = {"result": "GREEN", "tests": "bad", "gates": {"Doctor": "GREEN"}}
    current = {"result": "GREEN", "tests": 150, "gates": {"Doctor": "GREEN"}}
    report = compare_certifications(baseline, current)
    assert report.regression
    assert "Certification test count is invalid" in report.issues
