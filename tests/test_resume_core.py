"""恢复失败与诊断路径不依赖 SDK，也不创建缺失的数据库。"""

import json
import uuid

import pytest
from conftest import created_payload

from repropatch.cli import main
from repropatch.errors import StateReadError
from repropatch.events import EventLog, read_events
from repropatch.recovery import resume_run
from repropatch.resources import RunResources


def interrupted_preparation(task, tmp_path):
    run_id = uuid.uuid4().hex
    resources = RunResources(
        tmp_path / "runs", task.workspace_root, run_id, task.repository, task.revision
    )
    log = EventLog(resources.directory, run_id, lock=resources.lock)
    payload = created_payload(mode="run", engine="fake")
    payload["engine"].update(model_name=None, api_base=None, versions=None, use_env_proxy=False)
    payload.update(
        control_identity=resources.data()["control_identity"],
        workspace_identity=resources.data()["workspace_identity"],
    )
    log.emit("run_created", payload)
    log.emit("state_changed", {"from": "CREATED", "to": "PREPARING"})
    log.close()
    resources.close()
    return resources.directory


def test_core_resume_refuses_preparation_without_loading_model(task, tmp_path, monkeypatch):
    import sys

    directory = interrupted_preparation(task, tmp_path)
    monkeypatch.setitem(sys.modules, "agents", None)
    monkeypatch.setitem(sys.modules, "openai", None)
    monkeypatch.setitem(sys.modules, "repropatch.models", None)
    report = resume_run(directory)
    assert report["outcome"] == "RECOVERY_FAILED"
    assert report["reason_code"] == "UNSUPPORTED_RECOVERY_PHASE"
    assert report["artifacts_complete"] and report["agent"]["steps_used"] == 0
    assert report["provenance"]["implementation_sha256"]
    assert report["task_original"] is None and report["task_resolved"] is None
    assert report["baseline"] is None and report["candidate"] is None
    assert read_events(directory, directory.name).run["state"] == "FINISHED"


@pytest.mark.parametrize("damage", ["missing", "corrupt", "unknown_version"])
def test_resume_bad_database_never_creates_or_replaces_authority(task, tmp_path, damage):
    import sqlite3

    directory = interrupted_preparation(task, tmp_path)
    database = directory / "events.sqlite3"
    if damage == "missing":
        database.unlink()
    elif damage == "corrupt":
        database.write_bytes(b"corrupt original database")
    else:
        with sqlite3.connect(database) as db:
            db.execute("PRAGMA user_version=77")
    before = database.read_bytes() if database.exists() else None
    with pytest.raises(StateReadError, match="STATE_CORRUPT"):
        resume_run(directory)
    assert (database.read_bytes() if database.exists() else None) == before
    assert json.loads((directory / "recovery-error.json").read_text())["database_updated"] is False


def test_resume_invalid_identifier_is_static_error(tmp_path, capsys):
    assert main(["resume", "../run", "--root", str(tmp_path), "--json"]) == 2
    assert not list(tmp_path.iterdir())
    assert "RUN_ID" in capsys.readouterr().err


def test_legacy_database_is_readable_but_resume_does_not_migrate(task, tmp_path):
    import sqlite3

    directory = interrupted_preparation(task, tmp_path)
    database = directory / "events.sqlite3"
    with sqlite3.connect(database) as db:
        db.execute("DROP TABLE runs")
        db.execute("DROP TABLE checkpoints")
        db.execute("PRAGMA user_version=1")
    before = database.read_bytes()
    with pytest.raises(StateReadError, match="RESUME_UNSUPPORTED"):
        resume_run(directory)
    assert database.read_bytes() == before and read_events(directory, directory.name).version == 1
    assert not (directory / "recovery-error.json").exists()
