from pathlib import Path


def test_bob_docs_contains_non_negotiable_states():
    text = Path("docs/BOB-CONTROL-PLANE.md").read_text(encoding="utf-8")
    for state in ("NOT_TRIGGERED", "RUNNING", "FAILED", "VERIFIED", "ESCALATED"):
        assert state in text
