from runtime.certification_regression import compare_certifications


def test_no_regression_when_test_count_increases():
    baseline = {"result": "GREEN", "tests": 136, "gates": {"Doctor": "GREEN", "Regression suite": "GREEN"}}
    current = {"result": "GREEN", "tests": 138, "gates": {"Doctor": "GREEN", "Regression suite": "GREEN"}}
    report = compare_certifications(baseline, current)
    assert report.regression is False
    assert report.issues == []


def test_detects_test_count_drop():
    baseline = {"result": "GREEN", "tests": 136, "gates": {"Regression suite": "GREEN"}}
    current = {"result": "GREEN", "tests": 134, "gates": {"Regression suite": "GREEN"}}
    report = compare_certifications(baseline, current)
    assert report.regression is True
    assert "Regression suite tests dropped: 136 -> 134" in report.issues


def test_detects_gate_regression():
    baseline = {"result": "GREEN", "tests": 136, "gates": {"Memory health": "GREEN"}}
    current = {"result": "RED", "tests": 136, "gates": {"Memory health": "RED"}}
    report = compare_certifications(baseline, current)
    assert report.regression is True
    assert "Gate failed: Memory health" in report.issues


def test_first_run_has_no_regression():
    current = {"result": "GREEN", "tests": 136, "gates": {"Doctor": "GREEN"}}
    report = compare_certifications(None, current)
    assert report.regression is False
    assert report.issues == []


def test_malformed_baseline_is_reported():
    current = {"result": "GREEN", "tests": 136, "gates": {"Doctor": "GREEN"}}
    report = compare_certifications({"result": "GREEN"}, current)
    assert report.regression is True
    assert "Baseline certification is incomplete" in report.issues
