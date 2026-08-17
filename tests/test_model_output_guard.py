import pytest

from runtime.model_output_guard import guard_model_response


def test_guard_accepts_normal_response():
    payload = {"response": "hello", "done": True}
    assert guard_model_response(payload) == payload


def test_guard_rejects_missing_response():
    with pytest.raises(ValueError, match="missing or empty"):
        guard_model_response({"done": True})


def test_guard_bounds_large_response():
    result = guard_model_response({"response": "x" * 20_000})
    assert len(result["response"]) == 16_000
    assert result["response_truncated"] is True


def test_guard_rejects_invalid_budget():
    with pytest.raises(ValueError, match="max_chars"):
        guard_model_response({"response": "x"}, max_chars=0)
