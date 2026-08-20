from runtime.bob_control_loop import BobControlLoop
from runtime.policy import Capability, PolicyEngine, RiskLevel, ToolRequest


def test_blocked_job_never_reaches_executor():
    calls = []

    def executor(job):
        calls.append(job.job_id)
        return True

    loop = BobControlLoop(policy=PolicyEngine(), executor=executor)
    job = loop.submit("inspect repository", Capability.READ_REPOSITORY.value)
    result = loop.run_once(job.job_id)

    assert result.state.value == "succeeded"
    assert calls == [job.job_id]


def test_policy_denial_blocks_before_executor():
    calls = []
    loop = BobControlLoop(policy=PolicyEngine(), executor=lambda job: calls.append(job.job_id))
    job = loop.submit("modify repository", Capability.WRITE_REPOSITORY.value)

    assert job.state.value == "blocked"
    result = loop.run_once(job.job_id)
    assert result.state.value == "blocked"
    assert calls == []


def test_executor_failure_becomes_failed_and_is_audited():
    loop = BobControlLoop(policy=PolicyEngine(), executor=lambda job: False)
    job = loop.submit("inspect runtime", Capability.READ_RUNTIME.value)
    result = loop.run_once(job.job_id)

    assert result.state.value == "failed"
    assert any(event["event"] == "failure" for event in loop.audit)


def test_high_risk_request_requires_escalation():
    loop = BobControlLoop(policy=PolicyEngine(), executor=lambda job: True)
    job = loop.submit("inspect runtime", Capability.READ_RUNTIME.value, risk=RiskLevel.HIGH.value)

    assert job.state.value == "blocked"
    assert "approval" in (job.reason or "")
