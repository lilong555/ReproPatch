"""验证已提交事实、派生报告及只读查询的边界。"""

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest
from conftest import SimulatedSandbox, created_payload

from repropatch.artifacts import AuditBudget, EvidenceRef
from repropatch.cli import main
from repropatch.errors import StateWriteError
from repropatch.events import EventLog, read_events
from repropatch.harness import Harness
from repropatch.reports import committed_state, inspect_run


@pytest.fixture
def completed(task, tmp_path, external_patch):
    report = Harness(
        task,
        patch_file=external_patch(),
        producer="[不可信来源](javascript:alert(1)) <script>",
        output_root=tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
    ).run()
    assert report["outcome"] == "ACCEPTED" and report["artifacts_complete"]
    return Path(report["artifact_directory"]), report


def test_single_writer_snapshot_and_command_references(completed):
    directory, report = completed
    snapshot = read_events(directory, directory.name)
    assert snapshot.version == 2
    assert (directory / "events.jsonl").read_bytes() == snapshot.jsonl()
    rendered = (directory / "report.md").read_text()
    assert "\\[不可信来源\\]\\(javascript:alert\\(1\\)\\) &lt;script&gt;" in rendered
    assert report["trace"] == {
        "path": "events.jsonl",
        "sha256": hashlib.sha256(snapshot.jsonl()).hexdigest(),
        "size_bytes": len(snapshot.jsonl()),
    }
    assert committed_state(snapshot)["outcome"] == "ACCEPTED"
    assert snapshot.events[-2]["type"] == "cleanup_finished"
    assert snapshot.events[-1]["type"] == "state_changed"
    assert snapshot.events[-1]["payload"]["to"] == "FINISHED"
    starts = {
        event["operation_id"]: event
        for event in snapshot.events
        if event["type"] == "command_started"
    }
    finishes = [event for event in snapshot.events if event["type"] == "command_finished"]
    assert len(starts) == len(finishes) > 0
    for event in finishes:
        result = json.loads(
            EvidenceRef(**event["payload"]["result_ref"]).read(directory, limit=1024 * 1024)
        )
        assert result["command_id"] == event["operation_id"]
        assert starts[event["operation_id"]]["payload"]["argv"] == result["argv"]
        assert "stdout" not in event["payload"]
        for name in ("stdout_log", "stderr_log"):
            EvidenceRef(**result[name]).read(directory, limit=4 * 1024 * 1024)
    with sqlite3.connect(directory / "events.sqlite3") as db:
        assert db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall() == [("checkpoints",), ("events",), ("runs",)]


def test_no_jsonl_writes_and_transaction_failure_keeps_prefix(tmp_path):
    log = EventLog(tmp_path, "a" * 32)
    log.emit("run_created", created_payload())
    assert not (tmp_path / "events.jsonl").exists()
    log.db.execute(
        "CREATE TRIGGER reject_event BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT, '拒绝'); END"
    )
    log.db.commit()
    with pytest.raises(StateWriteError):
        log.emit("cleanup_finished", {})
    assert log.sequence == 1
    log.db.execute("DROP TRIGGER reject_event")
    log.emit("cleanup_finished", {})
    log.close()
    assert [event["seq"] for event in read_events(tmp_path, "a" * 32).events] == [1, 2]


def test_reports_rebuild_without_execution_or_sdk(completed, monkeypatch, capsys):
    directory, original = completed
    db_bytes = (directory / "events.sqlite3").read_bytes()
    for name in ("report.json", "report.md", "events.jsonl", "run.json"):
        (directory / name).unlink()
    assert not inspect_run(directory)["artifacts_complete"]
    for name in ("agents", "openai", "repropatch.models"):
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.setattr(Harness, "run", lambda _: pytest.fail("查询不得执行任务"))
    assert (
        main(["report", directory.name, "--root", str(directory.parent), "--format", "json"]) == 0
    )
    rebuilt = json.loads(capsys.readouterr().out)
    assert rebuilt["outcome"] == original["outcome"]
    assert rebuilt["usage"]["total_tokens"] is None
    assert rebuilt["engine"]["kind"] == "none"
    assert inspect_run(directory)["artifacts_complete"]
    assert (directory / "events.sqlite3").read_bytes() == db_bytes
    assert main(["inspect", directory.name, "--root", str(directory.parent), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["outcome"] == "ACCEPTED"


@pytest.mark.parametrize("failed", ["events.jsonl", "report.json", "report.md", "run.json"])
def test_export_failure_preserves_outcome_and_can_retry(
    task, tmp_path, external_patch, monkeypatch, failed, capsys
):
    write = AuditBudget.write

    def broken(self, name, content, **kwargs):
        if name == failed:
            raise OSError("注入导出失败")
        return write(self, name, content, **kwargs)

    monkeypatch.setattr(AuditBudget, "write", broken)
    report = Harness(
        task,
        patch_file=external_patch(),
        output_root=tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
    ).run()
    directory = Path(report["artifact_directory"])
    assert report["outcome"] == "ACCEPTED"
    assert report["command_error"] == "ARTIFACT_EXPORT_FAILED"
    if failed == "events.jsonl":
        assert report["trace"] is None
        assert json.loads((directory / "report.json").read_text())["trace"] is None
    query = inspect_run(directory)
    assert query["outcome"] == "ACCEPTED" and not query["artifacts_complete"]
    monkeypatch.setattr("repropatch.cli.Harness.run", lambda _: report)
    monkeypatch.setattr("repropatch.cli.Task.load", lambda _: task)
    assert main(["verify-patch", "fixture.yaml", "--patch", "unused", "--json"]) == 3
    output = capsys.readouterr()
    assert json.loads(output.out)["outcome"] == "ACCEPTED"
    assert "ARTIFACT_EXPORT_FAILED" in output.err
    assert main(["report", directory.name, "--root", str(directory.parent)]) == 3
    assert "ARTIFACT_EXPORT_FAILED" in capsys.readouterr().err
    monkeypatch.setattr(AuditBudget, "write", write)
    assert main(["report", directory.name, "--root", str(directory.parent)]) == 0
    capsys.readouterr()
    assert inspect_run(directory)["artifacts_complete"]
    assert committed_state(read_events(directory, directory.name))["outcome"] == "ACCEPTED"


def test_corrupt_evidence_never_rewrites_historical_outcome(completed, capsys):
    directory, report = completed
    ref = report["baseline"]["commands"][0]["stderr_log"]
    (directory / ref["path"]).write_bytes("损坏".encode())
    db_bytes = (directory / "events.sqlite3").read_bytes()
    query = inspect_run(directory)
    assert query["outcome"] == "ACCEPTED" and not query["evidence_complete"]
    assert (
        main(["report", directory.name, "--root", str(directory.parent), "--format", "json"]) == 3
    )
    output = capsys.readouterr()
    assert json.loads(output.out)["outcome"] == "ACCEPTED"
    assert "EVIDENCE_UNVERIFIABLE" in output.err
    assert (directory / "events.sqlite3").read_bytes() == db_bytes


def test_missing_final_fact_still_queries_committed_outcome(completed, capsys):
    directory, _ = completed
    (directory / "evidence/final-result.json").unlink()
    assert main(["inspect", directory.name, "--root", str(directory.parent), "--json"]) == 0
    query = json.loads(capsys.readouterr().out)
    assert query["outcome"] == "ACCEPTED" and not query["artifacts_complete"]
    assert main(["report", directory.name, "--root", str(directory.parent)]) == 3
    assert "EVIDENCE_UNVERIFIABLE" in capsys.readouterr().err


def test_uncommitted_run_never_uses_forged_report(tmp_path, capsys):
    directory = tmp_path / ("b" * 32)
    directory.mkdir(mode=0o700)
    log = EventLog(directory, directory.name)
    log.emit(
        "run_created",
        created_payload(),
    )
    log.emit("state_changed", {"from": "CREATED", "to": "PREPARING"})
    log.close()
    (directory / "report.json").write_text('{"outcome":"ACCEPTED"}')
    assert main(["inspect", directory.name, "--root", str(tmp_path), "--json"]) == 0
    query = json.loads(capsys.readouterr().out)
    assert query["state"] == "PREPARING" and query["outcome"] is None
    assert main(["report", directory.name, "--root", str(tmp_path)]) == 3
    assert "RUN_INCOMPLETE" in capsys.readouterr().err


@pytest.mark.parametrize("value", ["../bad", "a" * 8, "A" * 32, "g" * 32])
def test_cli_rejects_invalid_ids_before_filesystem(tmp_path, capsys, value):
    assert main(["inspect", value, "--root", str(tmp_path)]) == 2
    assert "RUN_ID_INVALID" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("kind", ["missing", "corrupt", "future", "symlink"])
def test_query_does_not_create_or_replace_bad_database(tmp_path, capsys, kind):
    directory = tmp_path / ("c" * 32)
    directory.mkdir()
    database = directory / "events.sqlite3"
    if kind == "corrupt":
        database.write_bytes(b"not sqlite")
    elif kind == "future":
        with sqlite3.connect(database) as db:
            db.execute("PRAGMA user_version=99")
    elif kind == "symlink":
        database.symlink_to(tmp_path / "absent")
    previous = database.read_bytes() if database.is_file() else None
    assert main(["inspect", directory.name, "--root", str(tmp_path), "--json"]) == 3
    assert "STATE_CORRUPT" in capsys.readouterr().err
    assert (database.read_bytes() if database.is_file() else None) == previous
    if kind == "missing":
        assert not database.exists()


def test_unexpected_error_keeps_cause_and_traceback(task, tmp_path, external_patch):
    class Broken(SimulatedSandbox):
        def run(self, argv):
            try:
                raise ValueError("根因哨兵")
            except ValueError as exc:
                raise RuntimeError("执行异常") from exc

    report = Harness(
        task,
        patch_file=external_patch(),
        output_root=tmp_path / "runs",
        sandbox_factory=Broken,
    ).run()
    assert report["outcome"] == "ERROR" and report["reason_code"] == "INTERNAL_ERROR"
    directory = Path(report["artifact_directory"])
    diagnostics = b"".join(
        EvidenceRef(**ref).read(directory, limit=1024 * 1024)
        for ref in report["diagnostics"]
        if ref["path"].endswith(".txt")
    )
    assert "根因哨兵".encode() in diagnostics and b"Traceback" in diagnostics
    assert report["cleanup"]["active_code_stopped"]


def test_failed_final_transaction_does_not_fabricate_finished(
    task, tmp_path, external_patch, monkeypatch
):
    emit = EventLog.emit

    def reject_final(self, event_type, payload, **kwargs):
        if event_type == "state_changed" and payload["to"] == "FINISHED":
            raise StateWriteError("STATE_WRITE_FAILED: 注入最终事务失败")
        return emit(self, event_type, payload, **kwargs)

    monkeypatch.setattr(EventLog, "emit", reject_final)
    harness = Harness(
        task,
        patch_file=external_patch(),
        output_root=tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
    )
    with pytest.raises(StateWriteError):
        harness.run()
    query = inspect_run(harness.directory)
    assert query["outcome"] is None and query["state"] == "VERIFYING"
    assert not (harness.directory / "report.json").exists()


def test_legacy_kind_audit_is_read_without_migration(tmp_path, capsys):
    directory = tmp_path / ("d" * 32)
    directory.mkdir()
    database = directory / "events.sqlite3"
    with sqlite3.connect(database) as db:
        db.execute(
            "CREATE TABLE events (seq INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, "
            "run_id TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL)"
        )
        db.execute(
            "INSERT INTO events VALUES (1, '2026-10-20T00:00:00+00:00', ?, 'run_finished', ?)",
            (directory.name, '{"outcome":"REJECTED","reason_code":"NO_PATCH"}'),
        )
    before = database.read_bytes()
    assert main(["inspect", directory.name, "--root", str(tmp_path), "--json"]) == 0
    query = json.loads(capsys.readouterr().out)
    assert query["event_format"] == 0 and query["outcome"] == "REJECTED"
    assert database.read_bytes() == before
