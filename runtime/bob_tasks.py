from __future__ import annotations

from enum import Enum


class TaskState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class Task:
    _TRANSITIONS = {
        TaskState.QUEUED: {TaskState.RUNNING, TaskState.FAILED, TaskState.ESCALATED},
        TaskState.RUNNING: {TaskState.VERIFYING, TaskState.FAILED, TaskState.ESCALATED},
        TaskState.VERIFYING: {TaskState.COMPLETED, TaskState.FAILED, TaskState.ESCALATED},
        TaskState.COMPLETED: set(),
        TaskState.FAILED: set(),
        TaskState.ESCALATED: set(),
    }

    def __init__(self, task_id: str):
        if not task_id.strip():
            raise ValueError("task_id must not be empty")
        self.task_id = task_id
        self.state = TaskState.QUEUED

    def _transition(self, target: TaskState) -> None:
        if target not in self._TRANSITIONS[self.state]:
            raise ValueError(f"invalid task transition: {self.state} -> {target}")
        self.state = target

    def start(self) -> None:
        self._transition(TaskState.RUNNING)

    def begin_verification(self) -> None:
        self._transition(TaskState.VERIFYING)

    def complete(self, *, verified: bool) -> None:
        if not verified:
            raise ValueError("task cannot complete without successful verification")
        self._transition(TaskState.COMPLETED)

    def fail(self) -> None:
        self._transition(TaskState.FAILED)

    def escalate(self) -> None:
        self._transition(TaskState.ESCALATED)
