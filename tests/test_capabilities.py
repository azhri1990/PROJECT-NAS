import pytest

from runtime.capabilities import CapabilityRegistry, CapabilitySpec


def test_registry_lists_capabilities_without_granting_execution_authority():
    registry = CapabilityRegistry()
    registry.register(
        CapabilitySpec(
            name="generator.code",
            category="generator",
            description="Generate source code locally.",
            provider="local-python",
            cost="free",
        )
    )

    found = registry.get("generator.code")
    assert found.description == "Generate source code locally."
    assert found.authorizes_execution is False
    assert registry.list()[0].name == "generator.code"


def test_registry_rejects_duplicate_names():
    registry = CapabilityRegistry()
    spec = CapabilitySpec(
        name="maps.lookup",
        category="geospatial",
        description="Look up a location.",
        provider="local-adapter",
        cost="free",
    )
    registry.register(spec)
    with pytest.raises(ValueError):
        registry.register(spec)
