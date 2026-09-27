import pytest

from runtime.bob_tasks import Task, TaskState


def test_task_lifecycle_completes_after_verified_result():
    task = Task("t1")
    assert task.state is TaskState.QUEUED
    task.start()
    task.begin_verification()
    task.complete(verified=True)
    assert task.state is TaskState.COMPLETED


def test_task_cannot_complete_without_verification():
    task = Task("t1")
    task.start()
    with pytest.raises(ValueError):
        task.complete(verified=False)
