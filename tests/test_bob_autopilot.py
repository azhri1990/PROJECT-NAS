from runtime.bob_autopilot import AutopilotAction, AutopilotDecision, decide_next


def test_routine_verified_work_proceeds():
    result = decide_next(
        risk="routine",
        verified=True,
        attempt=0,
        max_retries=2,
    )
    assert result == AutopilotDecision(AutopilotAction.PROCEED, "routine work is verified")


def test_missing_verification_fails_closed():
    result = decide_next(
        risk="routine",
        verified=False,
        attempt=0,
        max_retries=2,
    )
    assert result.action is AutopilotAction.ESCALATE
    assert "verification" in result.reason.lower()


def test_high_risk_escalates():
    result = decide_next(
        risk="security",
        verified=True,
        attempt=0,
        max_retries=2,
    )
    assert result.action is AutopilotAction.ESCALATE


def test_failed_routine_retries_within_bound():
    result = decide_next(
        risk="routine",
        verified=False,
        attempt=1,
        max_retries=2,
        failure_class="test_failure",
    )
    assert result.action is AutopilotAction.RETRY
    assert result.attempt == 2


def test_retry_budget_exhaustion_escalates():
    result = decide_next(
        risk="routine",
        verified=False,
        attempt=2,
        max_retries=2,
        failure_class="test_failure",
    )
    assert result.action is AutopilotAction.ESCALATE
