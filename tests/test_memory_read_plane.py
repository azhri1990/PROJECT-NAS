import runtime.tool_gateway as tool_gateway
from runtime.policy import Capability, RiskLevel


def test_gateway_bounds_aggregate_memory_context():
    gateway = tool_gateway.ToolGateway()
    gateway.register(
        tool_gateway.ToolSpec(
            "memory.read",
            Capability.READ_RUNTIME,
            RiskLevel.LOW,
            lambda payload: payload,
            lambda payload: {
                "memories": [
                    {"id": "one", "document": "A" * 3000, "metadata": {}},
                    {"id": "two", "document": "B" * 3000, "metadata": {}},
                    {"id": "three", "document": "C" * 3000, "metadata": {}},
                ],
                "count": 3,
            },
        )
    )

    raw = gateway.execute("memory.read", {})
    bounded = tool_gateway._bound_memory_result(raw)

    assert bounded["count"] == 2
    assert sum(len(item["document"]) for item in bounded["memories"]) == 6000
    assert bounded["truncated"] is True


def test_gateway_memory_bound_preserves_metadata_and_ids():
    result = tool_gateway._bound_memory_result(
        {
            "memories": [
                {"id": "id-1", "document": "remember this", "metadata": {"source": "test"}}
            ],
            "count": 1,
        }
    )

    assert result == {
        "memories": [
            {"id": "id-1", "document": "remember this", "metadata": {"source": "test"}}
        ],
        "count": 1,
        "truncated": False,
    }
