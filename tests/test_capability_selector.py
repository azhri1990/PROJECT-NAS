from runtime.capability_selector import select_workers


def record(name, classification, capabilities, roles, disposition="OPTIONAL"):
    return {
        "name": name,
        "classification": classification,
        "capabilities": capabilities,
        "platform_roles": roles,
        "integration": "test",
        "security": "medium",
        "disposition": disposition,
        "reason": "test",
    }


def test_select_workers_matches_capability_and_platform_deterministically():
    records = [
        record("Remote", "WORKER", ["coding"], ["PC_BUILD"]),
        record("Core", "CORE", ["coding"], ["PC_BUILD"], "KEEP"),
        record("Mobile", "WORKER", ["coding"], ["ANDROID_EDGE"]),
    ]
    selected = select_workers(records, "coding", "PC_BUILD")
    assert [item["name"] for item in selected] == ["Core", "Remote"]


def test_select_workers_excludes_personal_and_ignored_records():
    records = [
        record("Personal", "PERSONAL", ["coding"], ["ANDROID_EDGE"]),
        record("Ignored", "IGNORE", ["coding"], ["ANDROID_EDGE"], "IGNORE"),
        record("Worker", "WORKER", ["coding"], ["ANDROID_EDGE"]),
    ]
    selected = select_workers(records, "coding", "ANDROID_EDGE")
    assert [item["name"] for item in selected] == ["Worker"]


def test_select_workers_returns_empty_for_no_match():
    assert select_workers([], "coding", "PC_BUILD") == []
