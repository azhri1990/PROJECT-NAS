import pytest

from runtime.resource_aware_model_router import (
    ResourceAwareModelRouter,
    ResourceSnapshot,
    TaskComplexity,
)


def test_resource_snapshot_is_bounded_and_normalized():
    snapshot = ResourceSnapshot(ram_available_mb=512, cpu_load_ratio=0.9, cpu_count=4)
    assert snapshot.ram_available_mb == 512
    assert snapshot.cpu_load_ratio == 0.9
    assert snapshot.cpu_count == 4


def test_complex_task_selects_strong_model_when_resources_are_healthy():
    router = ResourceAwareModelRouter("llama3.2:3b", preferred_models=("llama3.2:3b", "llama3.2:1b"))
    route = router.route(
        available=("llama3.2:1b", "llama3.2:3b"),
        complexity=TaskComplexity.COMPLEX,
        resources=ResourceSnapshot(ram_available_mb=4096, cpu_load_ratio=0.2, cpu_count=8),
    )
    assert route.selected == "llama3.2:3b"
    assert not route.fallback


def test_resource_pressure_prefers_small_local_fallback():
    router = ResourceAwareModelRouter("llama3.2:3b", preferred_models=("llama3.2:3b", "llama3.2:1b"))
    route = router.route(
        available=("llama3.2:1b", "llama3.2:3b"),
        complexity=TaskComplexity.NORMAL,
        resources=ResourceSnapshot(ram_available_mb=700, cpu_load_ratio=0.95, cpu_count=4),
    )
    assert route.selected == "llama3.2:1b"
    assert route.fallback


def test_no_local_model_returns_no_model_instead_of_remote_fallback():
    router = ResourceAwareModelRouter("llama3.2:3b")
    route = router.route(
        available=(),
        complexity=TaskComplexity.COMPLEX,
        resources=ResourceSnapshot(ram_available_mb=8192, cpu_load_ratio=0.1, cpu_count=8),
    )
    assert route.selected is None
    assert route.reason == "no local model available"


def test_invalid_resource_snapshot_is_rejected():
    with pytest.raises(ValueError):
        ResourceSnapshot(ram_available_mb=-1, cpu_load_ratio=0.1, cpu_count=4)


def test_external_model_names_are_never_injected_by_resource_router():
    router = ResourceAwareModelRouter("llama3.2:3b")
    route = router.route(
        available=("https://example.com/model", "llama3.2:1b"),
        complexity=TaskComplexity.SIMPLE,
        resources=ResourceSnapshot(ram_available_mb=4096, cpu_load_ratio=0.1, cpu_count=8),
    )
    assert route.selected == "llama3.2:1b"
    assert all("/" not in name for name in route.available)
