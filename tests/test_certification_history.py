import json

from runtime.certification_history import CertificationHistory


def test_record_and_read_latest(tmp_path):
    history = CertificationHistory(tmp_path / "certification.jsonl", max_bytes=4096)
    history.record(
        timestamp="2026-08-18T12:00:00Z",
        commit="abc123",
        result="GREEN",
        tests=131,
        gates={"doctor": "GREEN", "regression": "GREEN"},
    )

    latest = history.latest()
    assert latest["result"] == "GREEN"
    assert latest["commit"] == "abc123"
    assert latest["tests"] == 131
    assert latest["gates"]["regression"] == "GREEN"


def test_red_result_is_recorded(tmp_path):
    history = CertificationHistory(tmp_path / "certification.jsonl")
    history.record(
        timestamp="2026-08-18T12:01:00Z",
        commit="def456",
        result="RED",
        tests=130,
        gates={"doctor": "RED"},
    )

    assert history.latest()["result"] == "RED"


def test_history_is_bounded_and_keeps_valid_jsonl(tmp_path):
    path = tmp_path / "certification.jsonl"
    history = CertificationHistory(path, max_bytes=700)
    for index in range(20):
        history.record(
            timestamp=f"2026-08-18T12:{index:02d}:00Z",
            commit=f"commit-{index}",
            result="GREEN",
            tests=131,
            gates={"regression": "GREEN", "doctor": "GREEN"},
        )

    assert path.stat().st_size <= 700
    records = history.records()
    assert records
    assert all(record["result"] == "GREEN" for record in records)
    assert history.latest()["commit"] == "commit-19"


def test_malformed_history_is_ignored_without_destroying_valid_records(tmp_path):
    path = tmp_path / "certification.jsonl"
    path.write_text('{"result":"GREEN","commit":"good"}\nnot-json\n', encoding="utf-8")

    history = CertificationHistory(path)
    assert history.records() == [{"result": "GREEN", "commit": "good"}]


def test_record_is_json_serializable(tmp_path):
    history = CertificationHistory(tmp_path / "certification.jsonl")
    history.record(
        timestamp="2026-08-18T12:00:00Z",
        commit="abc123",
        result="GREEN",
        tests=131,
        gates={"doctor": "GREEN"},
    )
    json.loads((tmp_path / "certification.jsonl").read_text(encoding="utf-8").splitlines()[0])
