from importlib import import_module

import pytest


bob_monitor = import_module("07-AUTOMATION.bob.resource_monitor")
bob_orchestrator = import_module("07-AUTOMATION.bob.autonomous_orchestrator")
bob_queue = import_module("07-AUTOMATION.bob.job_queue")

JobQueue = bob_queue.JobQueue
JobState = bob_queue.JobState
ResourceMonitor = bob_monitor.ResourceMonitor
ResourceSnapshot = bob_monitor.ResourceSnapshot
AutonomousOrchestrator = bob_orchestrator.AutonomousOrchestrator
RecoveryAction = bob_orchestrator.RecoveryAction
ResourceRequirements = bob_orchestrator.ResourceRequirements


def make_system():
    queue = JobQueue()
    resources = ResourceMonitor()
    orchestrator = AutonomousOrchestrator(queue, resources, max_retries=2)
    return queue, resources, orchestrator


def test_resource_snapshot_rejects_invalid_cpu():
    with pytest.raises(ValueError):
        ResourceSnapshot(cpu_load=1.1)


def test_orchestrator_defers_when_memory_is_low():
    queue, resources, orchestrator = make_system()
    job = queue.create("build", "process")
    resources.update("pc", ResourceSnapshot(memory_available_mb=512, cpu_load=0.2))

    decision = orchestrator.attempt(
        job,
        worker_id="pc",
        requirements=ResourceRequirements(min_memory_mb=2048),
    )

    assert decision.action == RecoveryAction.DEFER
    assert queue.get(job.job_id).state == JobState.CREATED


def test_orchestrator_starts_eligible_worker():
    queue, resources, orchestrator = make_system()
    job = queue.create("build", "process")
    resources.update("pc", ResourceSnapshot(memory_available_mb=4096, cpu_load=0.2))

    decision = orchestrator.attempt(
        job,
        worker_id="pc",
        requirements=ResourceRequirements(min_memory_mb=2048),
    )

    assert decision.action == RecoveryAction.NONE
    assert queue.get(job.job_id).state == JobState.RUNNING
    assert queue.get(job.job_id).worker_id == "pc"


def test_failure_retries_then_fails_closed():
    queue, _, orchestrator = make_system()
    job = queue.create("build", "process")

    first = orchestrator.failure(job, "worker disappeared")
    second = orchestrator.failure(queue.get(job.job_id), "worker disappeared")
    third = orchestrator.failure(queue.get(job.job_id), "worker disappeared")

    assert first.action == RecoveryAction.RETRY
    assert second.action == RecoveryAction.RETRY
    assert third.action == RecoveryAction.BLOCK
    assert queue.get(job.job_id).state == JobState.FAILED


def test_success_marks_job_complete():
    queue, resources, orchestrator = make_system()
    job = queue.create("build", "process")
    resources.update("pc", ResourceSnapshot(memory_available_mb=4096, cpu_load=0.1))
    orchestrator.attempt(job, worker_id="pc")

    decision = orchestrator.success(queue.get(job.job_id))

    assert decision.action == RecoveryAction.NONE
    assert queue.get(job.job_id).state == JobState.SUCCEEDED
