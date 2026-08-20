import pytest

from runtime.bob_resilience import FailureLedger, FailureRecord, RetryCircuitBreaker


def test_circuit_allows_attempts_below_threshold():
    breaker = RetryCircuitBreaker(max_failures=2)
    assert breaker.allow("job-a") is True
    breaker.record_failure("job-a")
    assert breaker.allow("job-a") is True


def test_circuit_opens_after_threshold_and_blocks_retry():
    breaker = RetryCircuitBreaker(max_failures=2)
    breaker.record_failure("job-a")
    breaker.record_failure("job-a")
    assert breaker.allow("job-a") is False
    assert breaker.is_open("job-a") is True


def test_success_resets_failure_counter():
    breaker = RetryCircuitBreaker(max_failures=2)
    breaker.record_failure("job-a")
    breaker.record_success("job-a")
    assert breaker.allow("job-a") is True
    assert breaker.failure_count("job-a") == 0


def test_invalid_threshold_is_rejected():
    with pytest.raises(ValueError):
        RetryCircuitBreaker(max_failures=0)


def test_failure_ledger_records_root_cause_and_prevention():
    ledger = FailureLedger(limit=2)
    ledger.record(FailureRecord("job-a", "executor error: TimeoutError", "dependency timeout", "retry with backoff"))
    assert ledger.recent("job-a")[0].prevention == "retry with backoff"


def test_failure_ledger_is_bounded():
    ledger = FailureLedger(limit=2)
    for index in range(3):
        ledger.record(FailureRecord(f"job-{index}", "failure", "cause", "prevention"))
    assert len(ledger.all()) == 2
    assert ledger.all()[0].job_id == "job-1"


def test_repeated_failure_opens_circuit_and_creates_incident():
    ledger = FailureLedger()
    breaker = RetryCircuitBreaker(max_failures=2, ledger=ledger)
    breaker.record_failure("job-a", reason="same failure")
    breaker.record_failure("job-a", reason="same failure")
    assert breaker.allow("job-a") is False
    incidents = ledger.recent("job-a")
    assert incidents[-1].prevention == "circuit opened; operator/root-cause review required"
