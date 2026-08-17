import pytest

from runtime.context_budget import ContextBudget, compose_context


def test_context_is_bounded_and_reports_truncation():
    context, truncated = compose_context("system", "M" * 100, "U" * 100, budget=ContextBudget(80))
    assert len(context) <= 80
    assert truncated is True
    assert "[SYSTEM]" in context


def test_user_section_is_preserved_when_budget_allows():
    context, truncated = compose_context("s", "m", "important user request", budget=ContextBudget(200))
    assert truncated is False
    assert "[USER]\nimportant user request" in context


def test_budget_has_hard_upper_bound():
    with pytest.raises(ValueError):
        ContextBudget(16001)
