import json

import pytest

from runtime.bob_learning import FailureLesson, LearningLedger


def lesson() -> FailureLesson:
    return FailureLesson(
        failure_class="ci-not-triggered",
        root_cause="workflow push trigger excluded the BOB branch",
        lesson="never infer CI state from a commit alone",
        prevention="verify trigger coverage and exact commit run",
        regression="assert the workflow runs for BOB branch pushes",
    )


def test_learning_ledger_persists_and_recovers_lessons(tmp_path):
    path = tmp_path / "lessons.json"
    ledger = LearningLedger(path)
    ledger.record(lesson())

    recovered = LearningLedger(path)
    assert recovered.known("ci-not-triggered")
    assert recovered.lessons_for("ci-not-triggered")[0] == lesson()
    assert recovered.should_escalate("ci-not-triggered") is True


def test_new_failure_class_does_not_escalate_until_recorded(tmp_path):
    ledger = LearningLedger(tmp_path / "lessons.json")
    assert ledger.should_escalate("new-class") is False
    ledger.record(lesson())
    assert ledger.should_escalate("new-class") is False


def test_invalid_lesson_is_rejected(tmp_path):
    ledger = LearningLedger(tmp_path / "lessons.json")
    invalid = FailureLesson("", "cause", "lesson", "prevention", "regression")
    with pytest.raises(ValueError):
        ledger.record(invalid)


def test_ledger_file_is_machine_readable(tmp_path):
    path = tmp_path / "lessons.json"
    LearningLedger(path).record(lesson())
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload[0]["failure_class"] == "ci-not-triggered"
