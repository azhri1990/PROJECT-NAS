import pytest

from runtime.certification_history import CertificationHistory
from runtime.certification_regression import compare_certifications


def test_history_rejects_single_record_that_exceeds_hard_bound(tmp_path):
    path = tmp_path / "history.jsonl"
    history = CertificationHistory(path, max_bytes=256)
    with pytest.raises(ValueError, match="exceeds history byte bound"):
        history.record(
            timestamp="2026-08-18T00:00:00Z",
            commit="a" * 40,
            result="GREEN",
            tests=150,
            gates={"x" * 500: "GREEN"},
        )
    assert not path.exists()


def test_history_trims_old_records_to_hard_bound(tmp_path):
    path = tmp_path / "history.jsonl"
    history = CertificationHistory(path, max_bytes=256)
    for index in range(20):
        history.record(
            timestamp=f"2026-08-18T00:{index:02d}:00Z",
            commit=f"{index:040d}",
            result="GREEN",
            tests=150 + index,
            gates={"Doctor": "GREEN"},
        )
    assert path.stat().st_size <= 256
    assert history.latest()["tests"] == 169


def test_regression_detects_missing_current_gate():
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
