from pathlib import Path

from runtime.adaptive_decision import OutcomeStatus, Strategy
from runtime.learning_loop_v3 import LearningLoopV3
from runtime.second_brain import SecondBrain


def test_learning_loop_metrics_are_bounded_and_deterministic(tmp_path: Path):
    brain = SecondBrain(tmp_path / "brain.sqlite3")
    brain.record_strategy(Strategy("local", "local verified path", risk=0.1, cost=0.1))
    loop = LearningLoopV3(brain, tmp_path / "learning_loop.sqlite3")
    observation = loop.observe("task", "local", "normal", "test")
    loop.record_outcome(observation, OutcomeStatus.SUCCESS, evidence=2)
    metrics = loop.metrics()
    assert metrics["observations"] == 1
    assert metrics["outcomes"] == 1
    assert metrics["measured_outcomes"] == 1
    assert metrics["success_rate"] == 1.0
    assert set(metrics) == {
        "observations", "outcomes", "successful_outcomes", "partial_outcomes",
        "failed_outcomes", "unknown_outcomes", "learning_updates", "measured_outcomes", "success_rate",
    }
