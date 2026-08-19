from pathlib import Path

from runtime.bob.android_activation import WorkerConfig, config_path, doctor, generate_worker_id, read_config, write_config


def test_generate_worker_id_is_scoped():
    worker_id = generate_worker_id()
    assert worker_id.startswith("android-")
    assert len(worker_id) > len("android-")


def test_config_round_trip_and_restricted_file(tmp_path: Path):
    config = WorkerConfig("android-test", "http://127.0.0.1:8000", "secret-token")
    path = write_config(config, tmp_path)
    assert path == config_path(tmp_path)
    assert read_config(tmp_path) == config
    assert path.exists()
    if hasattr(path.stat(), "st_mode"):
        assert path.stat().st_mode & 0o077 == 0


def test_doctor_rejects_missing_config(tmp_path: Path):
    result = doctor(tmp_path)
    assert result["ok"] is False
    assert result["checks"]["config"] is False


def test_doctor_accepts_valid_config(tmp_path: Path):
    write_config(WorkerConfig("android-test", "https://bob.local", "secret-token"), tmp_path)
    result = doctor(tmp_path)
    assert result["ok"] is True
    assert all(result["checks"].values())


def test_android_config_rejects_non_android_platform():
    try:
        WorkerConfig("worker", "http://localhost", "token", platform="pc")
    except ValueError as exc:
        assert "Android" in str(exc)
    else:
        raise AssertionError("non-Android platform must be rejected")
