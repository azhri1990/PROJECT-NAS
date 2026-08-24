from pathlib import Path

from runtime.adaptive_decision import Strategy
from runtime.bob_learning import BobFailureLearner
from runtime.second_brain import SecondBrain


def make_learner(tmp_path: Path) -> BobFailureLearner:
    brain = SecondBrain(tmp_path / "brain.sqlite3")
    brain.record_strategy(Strategy("worker-restart", "restart the failed worker", risk=0.2, cost=0.1))
    return BobFailureLearner(brain.learning_loop, failure_threshold=2)


def test_first_failure_records_lesson_and_allows_bounded_retry(tmp_path: Path):
    learner = make_learner(tmp_path)
    result = learner.observe_failure(
        task="restart worker",
        strategy_id="worker-restart",
        failure_class="heartbeat_timeout",
        context="heartbeat timeout",
        source="BOB supervisor",
        lesson="worker restart failed after heartbeat timeout",
    )
    assert result.action == "RETRY"
    assert result.failure_count == 1


def test_repeated_same_failure_class_escalates_and_is_persisted(tmp_path: Path):
    learner = make_learner(tmp_path)
    for _ in range(2):
        result = learner.observe_failure(
            task="restart worker",
            strategy_id="worker-restart",
            failure_class="heartbeat_timeout",
            context="heartbeat timeout",
            source="BOB supervisor",
            lesson="worker restart failed after heartbeat timeout",
        )
    assert result.action == "ESCALATE"
    assert result.failure_count == 2
    assert learner.loop.metrics()["failed_outcomes"] == 2


def test_different_failure_classes_do_not_cross_escalate(tmp_path: Path):
    learner = make_learner(tmp_path)
    first = learner.observe_failure(
        task="restart worker",
        strategy_id="worker-restart",
        failure_class="heartbeat_timeout",
        context="heartbeat timeout",
        source="BOB supervisor",
        lesson="worker restart failed after heartbeat timeout",
    )
    second = learner.observe_failure(
        task="restart worker",
        strategy_id="worker-restart",
        failure_class="network_timeout",
        context="network timeout",
        source="BOB supervisor",
        lesson="worker restart failed after network timeout",
    )
    assert first.failure_count == 1
    assert second.action == "RETRY"
    assert second.failure_count == 1
