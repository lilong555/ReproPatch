"""P2 外层事务与进程崩溃边界；不实现工具重做或自动恢复。"""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SimulatedSandbox, created_payload, scripted

from repropatch.artifacts import EvidenceRef
from repropatch.errors import InfrastructureError, StateReadError, StateWriteError
from repropatch.events import EventLog, encode_json, read_events
from repropatch.harness import Harness
from repropatch.reports import inspect_run


def prepare(directory, mode="run", engine="fake"):
    log = EventLog(directory, "a" * 32)
    log.emit("run_created", created_payload(mode, engine))
    log.emit("state_changed", {"from": "CREATED", "to": "PREPARING"})
    resolved = {
        "task_sha256": "b" * 64,
        "base_commit": "c" * 40,
        "image_id": "sha256:" + "d" * 64,
        "execution_contract": {"budget": {"wall_seconds": 60, "max_steps": 2, "max_tool_calls": 2}},
    }
    values = {
        "task_original": b"version: 2\n",
        "task_resolved": encode_json(resolved),
        "source_manifest": b"{}",
        "configuration": encode_json({"engine": {"kind": engine}}),
    }
    frozen = {
        name: vars(EvidenceRef.save(directory, name + ".json", value))
        for name, value in values.items()
    }
    frozen.update({name: resolved[name] for name in ("task_sha256", "base_commit", "image_id")})
    return log, frozen


def repairing(directory):
    log, frozen = prepare(directory)
    with log.transaction():
        log.emit("inputs_frozen", frozen)
        log.emit("state_changed", {"from": "PREPARING", "to": "REPRODUCING"})
    log.emit("state_changed", {"from": "REPRODUCING", "to": "REPAIRING"})
    reference = vars(EvidenceRef.save(directory, "native-input.json", b"{}"))
    payload = {
        "native_input": reference,
        "steps_used": 1,
        "usage": {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "synthetic": True,
            "unknown_turns": 1,
            "known_tokens": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        },
    }
    return log, payload


def test_three_tables_lock_and_execution_pragmas(tmp_path):
    log, _ = prepare(tmp_path)
    try:
        assert log.db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert log.db.execute("PRAGMA synchronous").fetchone()[0] == 2
        assert log.db.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
        assert {
            r[0] for r in log.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        } == {"runs", "events", "checkpoints"}
        before = (tmp_path / "events.sqlite3").read_bytes()
        command = (
            "from pathlib import Path; from repropatch.events import EventLog; "
            "import sys; EventLog.open_existing(Path(sys.argv[1]),'a'*32)"
        )
        child = subprocess.run(
            [sys.executable, "-c", command, str(tmp_path)], capture_output=True, timeout=10
        )
        assert child.returncode != 0 and b"BlockingIOError" in child.stderr
        assert (tmp_path / "events.sqlite3").read_bytes() == before
    finally:
        log.close()
    reopened = EventLog.open_existing(tmp_path, "a" * 32)
    assert reopened.state["state"] == "PREPARING"
    reopened.close()


def test_frozen_inputs_and_phase_share_one_commit(tmp_path):
    log, frozen = prepare(tmp_path)
    log.db.execute(
        "CREATE TRIGGER reject_phase BEFORE UPDATE OF state ON runs "
        "WHEN NEW.state='REPRODUCING' BEGIN SELECT RAISE(ABORT, '拒绝阶段'); END"
    )
    log.db.commit()
    try:
        with pytest.raises(StateWriteError):
            with log.transaction():
                log.emit("inputs_frozen", frozen)
                log.emit("state_changed", {"from": "PREPARING", "to": "REPRODUCING"})
        assert log.state["inputs_json"] is None and log.sequence == 2
        assert read_events(tmp_path, "a" * 32).last_seq == 2
        log.db.execute("DROP TRIGGER reject_phase")
        log.db.commit()
        with pytest.raises(StateWriteError):
            log.emit("inputs_frozen", frozen)
        with log.transaction():
            log.emit("inputs_frozen", frozen)
            log.emit("state_changed", {"from": "PREPARING", "to": "REPRODUCING"})
        snapshot = read_events(tmp_path, "a" * 32)
        assert snapshot.run["state"] == "REPRODUCING" and snapshot.run["inputs_json"]
        assert snapshot.last_seq == log.sequence == 4
    finally:
        log.close()


def test_illegal_transition_and_entry_cannot_escape_frozen_identity(tmp_path):
    log, frozen = prepare(tmp_path, "verify-patch", "none")
    try:
        with pytest.raises(StateWriteError):
            log.emit("state_changed", {"from": "PREPARING", "to": "VERIFYING"})
        with log.transaction():
            log.emit("inputs_frozen", frozen)
            log.emit("state_changed", {"from": "PREPARING", "to": "REPRODUCING"})
        with pytest.raises(StateWriteError):
            log.emit("state_changed", {"from": "REPRODUCING", "to": "REPAIRING"})
        (tmp_path / "configuration.json").write_bytes(b"changed")
        with pytest.raises(InfrastructureError, match="ARTIFACT_CORRUPT"):
            log.emit("state_changed", {"from": "REPRODUCING", "to": "VERIFYING"})
        assert log.state["state"] == "REPRODUCING" and log.sequence == 4
    finally:
        log.close()


@pytest.mark.parametrize("committed", [False, True])
def test_process_crash_preserves_atomic_model_start_and_budget(tmp_path, committed):
    log, payload = repairing(tmp_path)
    previous = log.sequence
    log.close()
    command = """
import json,os,sys
from pathlib import Path
from repropatch.events import EventLog
log=EventLog.open_existing(Path(sys.argv[1]),'a'*32)
payload=json.loads(sys.argv[2])
log.db.execute('PRAGMA cache_size=1')
if sys.argv[3] == 'True':
    log.emit('model_started',payload,step_id=1)
else:
    with log.transaction():
        log.emit('model_started',payload,step_id=1)
        log.emit('resource_registered',{'audit_padding':'x'*100000})
        os._exit(71)
os._exit(71)
"""
    child = subprocess.run(
        [sys.executable, "-c", command, str(tmp_path), json.dumps(payload), str(committed)],
        capture_output=True,
        timeout=15,
    )
    assert child.returncode == 71, child.stderr
    # 写控制器持锁后由 SQLite 原生回滚日志恢复，绝不由 JSONL 重建。
    reopened = EventLog.open_existing(tmp_path, "a" * 32)
    try:
        snapshot = read_events(tmp_path, "a" * 32)
        assert snapshot.run["steps_used"] == int(committed)
        assert snapshot.run["segment_open"] == int(committed)
        assert snapshot.last_seq == previous + int(committed)
        assert reopened.state == snapshot.run
        assert snapshot.run["deadline_at"] == created_deadline(snapshot)
    finally:
        reopened.close()


def test_tool_budget_cannot_be_refunded_or_admitted_above_frozen_limit(tmp_path):
    log, payload = repairing(tmp_path)
    try:
        log.emit("model_started", payload, step_id=1)
        calls = [
            {"name": "read_file", "tool_call_id": f"s000001.t0{i}", "provider_call_id": f"call-{i}"}
            for i in (1, 2)
        ]
        log.emit("tool_batch_admitted", {"calls": calls, "tool_calls_used": 2}, step_id=1)
        before = log.sequence
        for total, batch in ((3, calls[:1]), (1, [])):
            with pytest.raises(StateWriteError):
                log.emit(
                    "tool_batch_admitted", {"calls": batch, "tool_calls_used": total}, step_id=1
                )
        assert log.sequence == before
        snapshot = read_events(tmp_path, "a" * 32)
        assert snapshot.run["tool_calls_admitted"] == 2
        assert snapshot.run["steps_used"] == 1 and snapshot.run["segment_open"] == 1
    finally:
        log.close()


def created_deadline(snapshot):
    return snapshot.events[0]["payload"]["deadline_at"]


@pytest.mark.parametrize(
    "field,value", [("steps_used", 1), ("segment_open", 1), ("usage_json", "not json")]
)
def test_corrupt_state_never_falls_back_to_events_or_reports(tmp_path, field, value):
    log, _ = repairing(tmp_path)
    log.close()
    with sqlite3.connect(tmp_path / "events.sqlite3") as db:
        db.execute(f"UPDATE runs SET {field}=?", (value,))
    before = (tmp_path / "events.sqlite3").read_bytes()
    (tmp_path / "report.json").write_text('{"outcome":"ACCEPTED"}')
    with pytest.raises(StateReadError):
        read_events(tmp_path, "a" * 32)
    with pytest.raises(StateReadError):
        EventLog.open_existing(tmp_path, "a" * 32)
    assert (tmp_path / "events.sqlite3").read_bytes() == before


@pytest.mark.parametrize("kind", ["missing", "corrupt", "future", "symlink"])
def test_existing_writer_does_not_create_or_replace_invalid_database(tmp_path, kind):
    path = tmp_path / "events.sqlite3"
    if kind == "corrupt":
        path.write_bytes(b"not sqlite")
    elif kind == "future":
        with sqlite3.connect(path) as db:
            db.execute("PRAGMA user_version=99")
    elif kind == "symlink":
        path.symlink_to(tmp_path / "absent")
    if path.is_file():
        path.chmod(0o600)
    before = path.read_bytes() if path.is_file() else None
    with pytest.raises(StateReadError):
        EventLog.open_existing(tmp_path, "a" * 32)
    assert (path.read_bytes() if path.is_file() else None) == before
    if kind == "missing":
        assert not path.exists()


@pytest.mark.parametrize("database_version", [0, 1])
def test_p1_audit_is_readable_without_migration_or_resume(tmp_path, database_version):
    path = tmp_path / "events.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute(f"PRAGMA user_version={database_version}")
        p = created_payload()
        event = {
            "schema_version": 1,
            "run_id": "a" * 32,
            "seq": 1,
            "timestamp": p["created_at"],
            "type": "run_created",
            "step_id": None,
            "tool_call_id": None,
            "operation_id": None,
            "payload": p,
        }
        if database_version == 1:
            db.execute(
                "CREATE TABLE events (seq INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, "
                "type TEXT NOT NULL, envelope_json TEXT NOT NULL)"
            )
            db.execute(
                "INSERT INTO events VALUES (?,?,?,?)",
                (1, p["created_at"], "run_created", encode_json(event).decode()),
            )
        else:
            db.execute(
                "CREATE TABLE events (seq INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, "
                "run_id TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL)"
            )
            db.execute(
                "INSERT INTO events VALUES (?,?,?,?,?)",
                (1, p["created_at"], "a" * 32, "run_started", encode_json(p).decode()),
            )
    path.chmod(0o644 if database_version == 0 else 0o600)
    before = path.read_bytes()
    snapshot = read_events(tmp_path, "a" * 32)
    assert snapshot.version == database_version and snapshot.run is None and snapshot.events
    with pytest.raises(StateReadError, match="RESUME_UNSUPPORTED"):
        EventLog.open_existing(tmp_path, "a" * 32)
    assert path.read_bytes() == before


def test_missing_optional_sdk_keeps_explicit_error_and_zero_requests(task, tmp_path, monkeypatch):
    from importlib.metadata import PackageNotFoundError

    from repropatch import agent_runtime
    from repropatch.errors import ReproPatchError
    from repropatch.models import ResponsesConfig

    def missing(name):
        raise PackageNotFoundError(name)

    def unavailable():
        raise ReproPatchError("ENGINE_DEPENDENCY_MISSING: 缺少可选 SDK")

    monkeypatch.setattr("repropatch.harness.version", missing)
    monkeypatch.setattr("repropatch.models.prepare_sdk", unavailable)
    monkeypatch.setattr(agent_runtime, "prepare_sdk", unavailable)
    report = Harness(
        task,
        ResponsesConfig("contract-model", "https://contract.invalid", "UNUSED_TEST_KEY", True),
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
    ).run()
    assert report["reason_code"] == "ENGINE_DEPENDENCY_MISSING"
    assert report["agent"]["steps_used"] == report["agent"]["tool_calls_used"] == 0
    assert report["baseline"] is not None and report["independent"] is None


@pytest.mark.sdk
@pytest.mark.parametrize("failed", ["model_started", "tool_batch_admitted"])
def test_failed_runtime_transaction_prevents_model_or_tool_dispatch(
    task, tmp_path, monkeypatch, failed
):
    original = EventLog.__init__

    def injected(self, *args, **kwargs):
        original(self, *args, **kwargs)
        self.db.execute(
            f"CREATE TRIGGER refuse BEFORE INSERT ON events WHEN NEW.type='{failed}' "
            "BEGIN SELECT RAISE(ABORT,'注入事务失败'); END"
        )
        self.db.commit()

    monkeypatch.setattr(EventLog, "__init__", injected)
    model = scripted(
        [
            {
                "tool": "edit_file",
                "arguments": {
                    "path": "src/stats.cpp",
                    "old": "int best = 0;",
                    "new": "int best = samples.front();",
                },
            },
            {"finish": "完成"},
        ]
    )
    report = Harness(task, model, tmp_path / "runs", sandbox_factory=SimulatedSandbox).run()
    directory = Path(report["artifact_directory"])
    snapshot = read_events(directory, directory.name)
    assert report["outcome"] == "ERROR" and report["cleanup"]["active_code_stopped"]
    assert len(model.calls) == int(failed == "tool_batch_admitted")
    assert snapshot.run["steps_used"] == len(model.calls)
    assert snapshot.run["tool_calls_admitted"] == 0
    assert not any(e["type"] == "tool_started" for e in snapshot.events)
    assert not (directory / "patch.diff").read_bytes()


@pytest.mark.sdk
def test_sdk_observes_committed_segment_before_every_request(task, model, tmp_path, monkeypatch):
    harness = Harness(task, model, tmp_path / "runs", sandbox_factory=SimulatedSandbox)
    observed = []
    original = model.get_response

    async def checked(*args, **kwargs):
        snapshot = read_events(harness.directory, harness.directory.name)
        assert snapshot.events[-1]["type"] == "model_started"
        assert snapshot.run["steps_used"] == len(model.calls) + 1
        assert snapshot.run["segment_open"] == 1
        observed.append(snapshot.run["steps_used"])
        return await original(*args, **kwargs)

    monkeypatch.setattr(model, "get_response", checked)
    report = harness.run()
    snapshot = read_events(harness.directory, harness.directory.name)
    assert report["outcome"] == "ACCEPTED" and len(observed) == len(model.calls)
    assert snapshot.run["state"] == "FINISHED" and snapshot.run["segment_open"] == 1
    assert snapshot.run["steps_used"] == report["agent"]["steps_used"]
    assert snapshot.run["tool_calls_admitted"] == report["agent"]["tool_calls_used"]
    assert json.loads(snapshot.run["usage_json"]) == report["usage"]
    assert snapshot.run["last_checkpoint_id"] == len(model.calls)
    assert inspect_run(harness.directory)["artifacts_complete"]
    writer = EventLog.open_existing(harness.directory, harness.directory.name)
    try:
        with pytest.raises(StateWriteError):
            writer.emit("cleanup_finished", {})
        assert writer.sequence == snapshot.last_seq
    finally:
        writer.close()
