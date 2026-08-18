from pathlib import Path

from runtime.adaptive_decision import OutcomeStatus, Strategy
from runtime.learning_loop_v3 import LearningLoopV3
from runtime.second_brain import SecondBrain


def test_learning_loop_v3_end_to_end_metrics(tmp_path: Path):
    brain = SecondBrain(tmp_path / "brain.sqlite3")
    brain.record_strategy(Strategy("local", "local verified path", risk=0.1, cost=0.1))
    loop = LearningLoopV3(brain, tmp_path / "learning_loop.sqlite3")
    observation = loop.observe("task", "local", "normal", "test")
    result = loop.record_outcome(observation, OutcomeStatus.SUCCESS, evidence=2, lesson="local path is reliable")
    assert result.learned is True
    metrics = loop.metrics()
    assert metrics["observations"] == 1
    assert metrics["outcomes"] == 1
    assert metrics["successful_outcomes"] == 1
    assert metrics["learning_updates"] == 1
    assert metrics["success_rate"] == 1.0
