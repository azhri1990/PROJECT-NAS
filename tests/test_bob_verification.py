from runtime.bob_verification import VerificationState, evaluate_verification


def test_no_run_is_not_triggered():
    result = evaluate_verification("abc", None)
    assert result.state is VerificationState.NOT_TRIGGERED


def test_running_run_is_running():
    result = evaluate_verification("abc", {"status": "in_progress", "sha": "abc"})
    assert result.state is VerificationState.RUNNING


def test_failed_run_is_failed():
    result = evaluate_verification(
        "abc", {"status": "completed", "conclusion": "failure", "sha": "abc"}
    )
    assert result.state is VerificationState.FAILED


def test_success_requires_exact_sha():
    assert evaluate_verification(
        "abc", {"status": "completed", "conclusion": "success", "sha": "abc"}
    ).state is VerificationState.VERIFIED
    assert evaluate_verification(
        "abc", {"status": "completed", "conclusion": "success", "sha": "old"}
    ).state is VerificationState.NOT_TRIGGERED
