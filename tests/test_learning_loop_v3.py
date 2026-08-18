from pathlib import Path

import pytest

from runtime.adaptive_decision import OutcomeStatus, Strategy
from runtime.learning_loop_v3 import LearningLoopV3
from runtime.second_brain import SecondBrain


def make_loop(tmp_path: Path) -> LearningLoopV3:
    brain = SecondBrain(tmp_path / "brain.sqlite3")
    strategy = Strategy("local", "local verified path", risk=0.1, cost=0.1)
    brain.record_strategy(strategy)
    return LearningLoopV3(brain, tmp_path / "learning_loop.sqlite3")


def test_learning_loop_records_success_and_promotes_verified_lesson(tmp_path: Path):
    loop = make_loop(tmp_path)
    observation = loop.observe("answer task", "local", "normal", "test")
    result = loop.record_outcome(observation, OutcomeStatus.SUCCESS, evidence=2, lesson="local path is reliable")
    assert result.status is OutcomeStatus.SUCCESS
    assert result.learned is True
    assert loop.metrics()["successful_outcomes"] == 1
    assert loop.consolidate("local reliable")


def test_unknown_outcome_does_not_change_learning_metrics(tmp_path: Path):
    loop = make_loop(tmp_path)
    observation = loop.observe("answer task", "local", "normal", "test")
    loop.record_outcome(observation, OutcomeStatus.UNKNOWN, evidence=10, lesson="do not learn this")
    metrics = loop.metrics()
    assert metrics["unknown_outcomes"] == 1
    assert metrics["learning_updates"] == 0


def test_failure_is_recorded_and_can_feed_strategy_feedback(tmp_path: Path):
    loop = make_loop(tmp_path)
    observation = loop.observe("answer task", "local", "normal", "test")
    loop.record_outcome(observation, OutcomeStatus.FAILURE, evidence=1)
    assert loop.metrics()["failed_outcomes"] == 1
    assert loop.brain.strategy_history("local").failure_rate == 1.0


def test_consolidation_merges_duplicate_verified_lessons(tmp_path: Path):
    loop = make_loop(tmp_path)
    first = loop.observe("task one", "local", "normal", "test")
    loop.record_outcome(first, OutcomeStatus.SUCCESS, evidence=2, lesson="SQLite is the local memory backend")
    second = loop.observe("task two", "local", "normal", "test")
    loop.record_outcome(second, OutcomeStatus.SUCCESS, evidence=3, lesson="SQLite is the local memory backend")
    memories = loop.consolidate("SQLite local memory", limit=20)
    matching = [m for m in memories if m.statement == "SQLite is the local memory backend"]
    assert len(matching) == 1
    assert matching[0].evidence >= 5


def test_inputs_are_bounded_and_unknown_observation_is_rejected(tmp_path: Path):
    loop = make_loop(tmp_path)
    with pytest.raises(ValueError):
        loop.observe("", "local", "normal", "test")
    with pytest.raises(ValueError):
        loop.observe("x" * 1025, "local", "normal", "test")
    with pytest.raises(KeyError):
        loop.record_outcome("missing", OutcomeStatus.SUCCESS)
