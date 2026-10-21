"""轨迹查询、JSONL 导出与未知片段的只读边界。"""

import hashlib
import json
import sqlite3
import subprocess
import sys

import pytest
from conftest import created_payload
from test_checkpoints import contract_checkpoint
from test_events_reports import completed as completed

from repropatch.cli import main
from repropatch.errors import StateReadError
from repropatch.events import EventLog, read_events
from repropatch.trace import export_trace, replay_trace, trace_markdown


def frozen_files(directory):
    return {
        str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.rglob("*")
        if p.is_file()
    }


def no_execution(monkeypatch):
    from repropatch.harness import Harness
    from repropatch.sandbox import DockerSandbox
    from repropatch.tools import Toolbox

    def forbidden(*args, **kwargs):
        pytest.fail("只读轨迹不得调用模型、工具、Docker、Git 或恢复控制器")

    for module in ("agents", "openai", "repropatch.models"):
        monkeypatch.setitem(sys.modules, module, None)
    monkeypatch.setattr(Harness, "run", forbidden)
    monkeypatch.setattr(DockerSandbox, "__enter__", forbidden)
    monkeypatch.setattr(Toolbox, "run_command", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr("repropatch.recovery.resume_run", forbidden)


def test_trace_cli_is_readonly_without_sdk_or_processes(completed, monkeypatch, capsys):
    directory, report = completed
    before = frozen_files(directory)
    snapshot = read_events(directory, directory.name)
    no_execution(monkeypatch)
    assert (
        main(
            ["replay", directory.name, "--root", str(directory.parent), "--mode", "trace", "--json"]
        )
        == 0
    )
    trace = json.loads(capsys.readouterr().out)
    assert trace["state"] == "FINISHED" and trace["outcome"] == report["outcome"]
    assert trace["evidence_complete"] and len(trace["timeline"]) == snapshot.last_seq
    assert [row["seq"] for row in trace["timeline"]] == list(range(1, snapshot.last_seq + 1))
    assert main(["export-trace", directory.name, "--root", str(directory.parent)]) == 0
    assert capsys.readouterr().out.encode() == snapshot.jsonl()
    assert frozen_files(directory) == before


def test_trace_uses_database_when_derived_files_are_missing_or_forged(completed, monkeypatch):
    directory, _ = completed
    for name in ("run.json", "report.json", "report.md", "events.jsonl"):
        (directory / name).unlink()
    (directory / "events.jsonl").write_text('{"type":"fake_execution","outcome":"REJECTED"}\n')
    before = frozen_files(directory)
    no_execution(monkeypatch)
    trace = replay_trace(directory)
    assert trace["evidence_complete"] and trace["outcome"] == "ACCEPTED"
    assert export_trace(directory)[0] == read_events(directory, directory.name).jsonl()
    assert frozen_files(directory) == before


@pytest.mark.parametrize("kind", ["native", "producer"])
def test_open_segment_never_executes_and_opaque_attachments_are_not_displayed(
    tmp_path, monkeypatch, kind
):
    from test_recovery import repairing

    from repropatch.artifacts import EvidenceRef

    directory = tmp_path / ("a" * 32)
    directory.mkdir(mode=0o700)
    log, _ = repairing(directory)
    content = b'{"reasoning":{"encrypted_content":"private-opaque"}}'
    reference = vars(EvidenceRef.save(directory, kind + "/input.json", content))
    log.emit(
        "model_started",
        {
            "native_input": reference,
            "steps_used": 1,
            "usage": {
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
                "synthetic": True,
            },
        },
        step_id=1,
    )
    log.close()
    before = frozen_files(directory)
    no_execution(monkeypatch)
    trace = replay_trace(directory)
    assert trace["state"] == "REPAIRING" and trace["outcome"] is None
    assert trace["timeline"][-1]["type"] == "model_started"
    assert trace["timeline"][-1]["references"] == [reference]
    assert "private-opaque" not in json.dumps(trace) and "private-opaque" not in trace_markdown(
        trace
    )
    assert "private-opaque" not in export_trace(directory)[0].decode()
    assert frozen_files(directory) == before


def test_paused_checkpoint_is_only_read_and_missing_native_input_is_reported(
    tmp_path, monkeypatch, capsys
):
    directory = tmp_path / ("a" * 32)
    directory.mkdir(mode=0o700)
    manifest = contract_checkpoint(directory)
    log = EventLog.open_existing(directory, directory.name)
    log.emit("state_changed", {"from": "REPAIRING", "to": "INTERRUPTED", "pause_after_step": 1})
    log.close()
    before = frozen_files(directory)
    no_execution(monkeypatch)
    trace = replay_trace(directory)
    assert (
        trace["state"] == "INTERRUPTED" and trace["outcome"] is None and trace["evidence_complete"]
    )
    assert frozen_files(directory) == before
    path = directory / manifest["native_next_input"]["path"]
    path.unlink()
    damaged = frozen_files(directory)
    args = [directory.name, "--root", str(directory.parent)]
    assert main(["replay", *args, "--mode", "trace", "--json"]) == 3
    trace = json.loads(capsys.readouterr().out)
    assert trace["state"] == "INTERRUPTED" and not trace["evidence_complete"] and trace["timeline"]
    assert main(["export-trace", *args]) == 3
    captured = capsys.readouterr()
    assert captured.out.encode() == read_events(directory, directory.name).jsonl()
    assert "EVIDENCE_UNVERIFIABLE" in captured.err and frozen_files(directory) == damaged


def test_missing_nested_evidence_keeps_authoritative_outcome(completed, monkeypatch, capsys):
    directory, report = completed
    (directory / report["baseline"]["commands"][0]["stdout_log"]["path"]).unlink()
    before = frozen_files(directory)
    no_execution(monkeypatch)
    assert (
        main(
            ["replay", directory.name, "--root", str(directory.parent), "--mode", "trace", "--json"]
        )
        == 3
    )
    result = json.loads(capsys.readouterr().out)
    assert result["outcome"] == "ACCEPTED" and not result["evidence_complete"]
    assert result["evidence_errors"] and frozen_files(directory) == before


def test_explicit_export_creates_exact_new_file_without_touching_run(completed, tmp_path):
    directory, _ = completed
    before = frozen_files(directory)
    target = tmp_path / "exports" / "trace.jsonl"
    content, problems = export_trace(directory, target)
    assert not problems and target.read_bytes() == content
    assert target.stat().st_mode & 0o777 == 0o600
    assert [json.loads(line)["seq"] for line in content.splitlines()] == list(
        range(1, read_events(directory, directory.name).last_seq + 1)
    )
    assert frozen_files(directory) == before


@pytest.mark.parametrize(
    "destination", ["database", "existing", "symlink", "parent_link", "traversal"]
)
def test_export_never_overwrites_or_follows_links(completed, tmp_path, destination, capsys):
    directory, _ = completed
    target = tmp_path / "trace.jsonl"
    original = tmp_path / "sentinel"
    original.write_bytes(b"keep")
    if destination == "database":
        target = directory / "events.sqlite3"
    elif destination == "existing":
        target.write_bytes(b"keep")
    elif destination == "symlink":
        target.symlink_to(original)
    elif destination == "traversal":
        target = directory / "nested" / ".." / "extra.jsonl"
    else:
        link = tmp_path / "linked"
        link.symlink_to(directory, target_is_directory=True)
        target = link / "extra.jsonl"
    before = frozen_files(directory)
    assert (
        main(
            [
                "export-trace",
                directory.name,
                "--root",
                str(directory.parent),
                "--output",
                str(target),
            ]
        )
        == 3
    )
    assert original.read_bytes() == b"keep" and frozen_files(directory) == before
    assert not list(tmp_path.glob(".repropatch-trace-*"))
    assert not capsys.readouterr().out


@pytest.mark.parametrize("damage", ["missing", "corrupt", "empty"])
def test_unknown_database_cannot_be_exported_as_empty_success(tmp_path, damage, capsys):
    directory = tmp_path / ("a" * 32)
    directory.mkdir(mode=0o700)
    database = directory / "events.sqlite3"
    if damage == "corrupt":
        database.write_bytes(b"not sqlite")
    elif damage == "empty":
        with sqlite3.connect(database) as db:
            db.execute(
                "CREATE TABLE events (seq INTEGER PRIMARY KEY,timestamp TEXT,"
                "type TEXT,envelope_json TEXT)"
            )
            db.execute("PRAGMA user_version=1")
    before = frozen_files(directory)
    target = tmp_path / "trace.jsonl"
    assert (
        main(["export-trace", directory.name, "--root", str(tmp_path), "--output", str(target)])
        == 3
    )
    assert not target.exists() and frozen_files(directory) == before
    assert not capsys.readouterr().out


@pytest.mark.parametrize("version", [0, 1])
def test_trace_preserves_known_legacy_format_without_migration(tmp_path, version):
    directory = tmp_path / ("a" * 32)
    directory.mkdir(mode=0o700)
    if version == 0:
        with sqlite3.connect(directory / "events.sqlite3") as db:
            db.execute(
                "CREATE TABLE events (seq INTEGER PRIMARY KEY,timestamp TEXT,"
                "run_id TEXT,kind TEXT,payload TEXT)"
            )
            db.execute(
                "INSERT INTO events VALUES (1,?,?,?,?)",
                (
                    "2026-10-19T00:00:00+00:00",
                    directory.name,
                    "run_started",
                    json.dumps({"task_id": "legacy", "input_mode": "run"}),
                ),
            )
    else:
        log = EventLog(directory, directory.name)
        log.emit("run_created", created_payload())
        log.close()
        with sqlite3.connect(directory / "events.sqlite3") as db:
            db.execute("DROP TABLE runs")
            db.execute("DROP TABLE checkpoints")
            db.execute("PRAGMA user_version=1")
    before = frozen_files(directory)
    trace = replay_trace(directory)
    assert trace["database_version"] == version
    assert trace["evidence_complete"] is (None if version == 0 else True)
    if version == 0:
        with pytest.raises(StateReadError, match="EVENT_FORMAT_UNSUPPORTED"):
            export_trace(directory)
    else:
        assert export_trace(directory)[0] == read_events(directory, directory.name).jsonl()
    assert frozen_files(directory) == before


def test_markdown_escapes_untrusted_event_values(tmp_path):
    directory = tmp_path / ("a" * 32)
    directory.mkdir(mode=0o700)
    log = EventLog(directory, directory.name)
    log.emit("run_created", created_payload())
    log.emit(
        "command_started",
        {"argv": ["sh", "-lc", "<script>|\x1b[31m\nunsafe"], "cwd": "/build"},
        operation_id="b" * 32,
    )
    log.close()
    text = trace_markdown(replay_trace(directory))
    assert "\x1b" not in text and "<script>" not in text
    event_line = next(line for line in text.splitlines() if line.startswith("| 2 |"))
    assert "&lt;script&gt;" in text and "\\x1b" in text
    assert event_line.count("|") == 6 and "unsafe" in event_line
