from unittest.mock import Mock, patch

import requests
import pytest

from runtime.local_model_router import LocalModelRouter


def test_generate_with_fallback_retries_after_connection_error():
    router = LocalModelRouter("llama3.2:3b")
    fallback = Mock(return_value={"response": "ok"})

    with patch.object(router, "generate", side_effect=[requests.ConnectionError("offline"), {"response": "ok"}]) as generate, patch.object(router, "discover_route", return_value=router.route(("llama3.2:1b",))):
        result, route = router.generate_with_fallback("hello")

    assert result["response"] == "ok"
    assert route.selected == "llama3.2:1b"
    assert generate.call_count == 2


def test_generate_with_fallback_retries_after_timeout():
    router = LocalModelRouter("llama3.2:3b")

    with patch.object(router, "generate", side_effect=[requests.Timeout("timeout"), {"response": "ok"}]), patch.object(router, "discover_route", return_value=router.route(("llama3.2:1b",))):
        result, route = router.generate_with_fallback("hello")

    assert result["response"] == "ok"
    assert route.selected == "llama3.2:1b"


def test_generate_with_fallback_does_not_hide_unexpected_http_error():
    router = LocalModelRouter("llama3.2:3b")
    response = Mock(status_code=500)
    error = requests.HTTPError("server error", response=response)

    with patch.object(router, "generate", side_effect=error):
        with pytest.raises(requests.HTTPError):
            router.generate_with_fallback("hello")


def test_generate_with_fallback_reports_no_local_fallback():
    router = LocalModelRouter("llama3.2:3b")

    with patch.object(router, "generate", side_effect=requests.ConnectionError("offline")), patch.object(router, "discover_route", return_value=router.route(())):
        with pytest.raises(RuntimeError, match="no fallback model"):
            router.generate_with_fallback("hello")
