"""完整输入 Checkpoint、不可变附件与受控暂停的外部可观察边界。"""

import hashlib
import json
import subprocess
import sys
from dataclasses import replace

import pytest
from conftest import ROOT, SimulatedSandbox, scripted
from test_recovery import prepare

from repropatch.artifacts import AuditBudget, EvidenceRef
from repropatch.cli import main
from repropatch.errors import InfrastructureError
from repropatch.events import encode_json, read_events
from repropatch.harness import Harness
from repropatch.recovery import read_checkpoint
from repropatch.reports import inspect_run
from repropatch.resources import RunLock
from repropatch.task import Task, canonical_json
from repropatch.workspace import SourceManifest


def contract_checkpoint(root, mutate=None):
    """仅用于格式校验的合成文件；执行安全性由真实 Harness/SDK 测试证明。"""
    log, frozen = prepare(root)
    resolved_reference = frozen["task_resolved"]
    resolved = json.loads(EvidenceRef(**resolved_reference).read(root, limit=256 * 1024))
    resolved["workspace_root"] = str(root / "workspaces")
    frozen["task_resolved"] = vars(
        EvidenceRef.save(root, resolved_reference["path"], encode_json(resolved))
    )
    config = {
        "engine": {"kind": "fake"},
        "harness_version": "fixture",
        "implementation_sha256": "e" * 64,
        "python": "3.12",
        "sdk_versions": {"fixture": "1"},
    }
    config_ref = vars(EvidenceRef.save(root, "configuration.json", encode_json(config)))
    frozen["configuration"] = config_ref
    EvidenceRef.save(root, "configuration.json", encode_json(config))
    with log.transaction():
        log.emit("inputs_frozen", frozen)
        log.emit("state_changed", {"from": "PREPARING", "to": "REPRODUCING"})
    baseline_ref = vars(
        EvidenceRef.save(root, "baseline.json", b'{"cleanup":{"confirmed":true},"isolated":false}')
    )
    log.emit(
        "baseline_finished",
        {"outcome": None, "reason_code": "BASELINE_PASSED", "evidence": baseline_ref},
    )
    log.emit("state_changed", {"from": "REPRODUCING", "to": "REPAIRING"})
    log.emit(
        "model_started",
        {
            "native_input": vars(EvidenceRef.save(root, "native-input.json", b"{}")),
            "steps_used": 1,
            "engine": {"kind": "fake", "model_name": None, "api_base": None, "versions": None},
            "usage": {
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
                "synthetic": True,
            },
        },
        step_id=1,
    )
    prefix = "checkpoints/1"

    def save(name, value):
        return vars(EvidenceRef.save(root, prefix + "/" + name, value))

    native = {"instructions": "fixture", "input": [{"role": "user", "content": "fixture"}]}
    source = SourceManifest(())
    manifest = {
        "schema_version": 1,
        "checkpoint_id": 1,
        "boundary": "model_input_ready",
        "step_id": 1,
        "input_fingerprints": {
            **{key: log.state[key] for key in ("task_sha256", "base_commit", "image_id")},
            **{
                key: config[key]
                for key in ("harness_version", "implementation_sha256", "python", "sdk_versions")
            },
            "configuration": config_ref,
            "tools_sha256": "f" * 64,
            "instructions_sha256": hashlib.sha256(canonical_json("fixture")).hexdigest(),
        },
        "baseline": baseline_ref,
        "native_next_input": save("next-input.json", canonical_json(native) + b"\n"),
        "patch": save("patch.diff", b""),
        "source_manifest": save(
            "source-manifest.json", json.dumps(source.to_dict(), indent=2).encode()
        ),
        "source_tree_sha256": source.sha256,
        "counters": {"steps_used": 1, "tool_calls_admitted": 0},
        "deadline_at": log.state["deadline_at"],
    }
    if mutate:
        mutate(manifest, native, save)
    ref = save("manifest.json", canonical_json(manifest))
    log.emit(
        "checkpoint_committed",
        {
            "checkpoint_id": 1,
            "step_id": 1,
            "manifest_ref": ref,
            "counters": {"steps_used": 1, "tool_calls_admitted": 0},
        },
        step_id=1,
    )
    log.close()
    return manifest


def test_checkpoint_preserves_empty_patch_and_distinct_source_hashes(tmp_path):
    expected = contract_checkpoint(tmp_path)
    manifest, _ = read_checkpoint(tmp_path, read_events(tmp_path, "a" * 32))
    assert manifest == expected
    assert manifest["patch"]["size_bytes"] == 0
    assert manifest["source_tree_sha256"] != manifest["source_manifest"]["sha256"]


@pytest.mark.parametrize(
    "name",
    ["manifest.json", "next-input.json", "patch.diff", "source-manifest.json", "baseline.json"],
)
def test_missing_or_changed_checkpoint_evidence_is_not_a_recovery_point(tmp_path, name):
    contract_checkpoint(tmp_path)
    path = tmp_path / (name if name == "baseline.json" else "checkpoints/1/" + name)
    path.write_bytes(path.read_bytes() + b"changed")
    before = (tmp_path / "events.sqlite3").read_bytes()
    with pytest.raises(InfrastructureError, match="CHECKPOINT_CORRUPT"):
        read_checkpoint(tmp_path, read_events(tmp_path, "a" * 32))
    assert (tmp_path / "events.sqlite3").read_bytes() == before


@pytest.mark.parametrize(
    "invalid", ["version", "counter", "deadline", "source_hash", "instructions_hash", "native"]
)
def test_valid_file_hash_does_not_override_checkpoint_invariants(tmp_path, invalid):
    def mutate(manifest, native, save):
        if invalid == "version":
            manifest["schema_version"] = 2
        elif invalid == "counter":
            manifest["counters"]["tool_calls_admitted"] = 1
        elif invalid == "deadline":
            manifest["deadline_at"] = "2099-01-01T00:00:00+00:00"
        elif invalid == "source_hash":
            manifest["source_tree_sha256"] = "0" * 64
        elif invalid == "instructions_hash":
            manifest["input_fingerprints"]["instructions_sha256"] = "0" * 64
        else:
            manifest["native_next_input"] = save(
                "next-input.json", b'{"input":[],"instructions":"x","pending":[]}'
            )

    contract_checkpoint(tmp_path, mutate)
    with pytest.raises(InfrastructureError, match="CHECKPOINT_CORRUPT"):
        read_checkpoint(tmp_path, read_events(tmp_path, "a" * 32))


def test_orphan_directory_never_replaces_database_checkpoint(tmp_path):
    contract_checkpoint(tmp_path)
    orphan = tmp_path / "checkpoints/999"
    orphan.mkdir()
    (orphan / "manifest.json").write_text("{}")
    snapshot = read_events(tmp_path, "a" * 32)
    assert read_checkpoint(tmp_path, snapshot)[0]["checkpoint_id"] == 1
    with pytest.raises(InfrastructureError, match="CHECKPOINT_CORRUPT"):
        read_checkpoint(tmp_path, snapshot, 999)


def test_inspect_does_not_claim_complete_evidence_for_invalid_paused_manifest(tmp_path):
    from repropatch.events import EventLog

    root = tmp_path / ("a" * 32)
    root.mkdir(mode=0o700)
    contract_checkpoint(
        root, lambda manifest, native, save: manifest.update(source_tree_sha256="0" * 64)
    )
    log = EventLog.open_existing(root, root.name)
    log.emit("state_changed", {"from": "REPAIRING", "to": "INTERRUPTED", "pause_after_step": 1})
    log.close()
    result = inspect_run(root)
    assert not result["artifacts_complete"] and not result["evidence_complete"]
    assert any("CHECKPOINT_CORRUPT" in message for message in result["errors"])


@pytest.mark.parametrize("step", [0, -1, 8])
def test_pause_argument_rejected_before_run_or_optional_sdk(step, monkeypatch, capsys):
    monkeypatch.setattr(
        "repropatch.cli.Harness", lambda *a, **kw: pytest.fail("无效暂停参数不能创建 Run")
    )
    task = ROOT / "examples/tasks/negative-maximum.v2.yaml"
    step = Task.load(task).budget.max_steps if step == 8 else step
    assert (
        main(["run", str(task), "--pause-after-step", str(step), "--mock-script", "unused.json"])
        == 2
    )
    assert "PAUSE_STEP_INVALID" in capsys.readouterr().err


@pytest.mark.sdk
@pytest.mark.parametrize("retain", ["none", "on_failure", "always"])
def test_pause_keeps_source_and_complete_native_boundary_without_next_request(
    task, tmp_path, retain
):
    from repropatch.models import load_sdk_script

    model, source = load_sdk_script(
        ROOT / "examples/models/fix-negative-maximum.json", with_source=True
    )
    task = replace(task, retain=retain)
    h = Harness(
        task,
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        pause_after_step=3,
        script_source=source,
    )
    report = h.run()
    snapshot = read_events(h.directory, h.directory.name)
    manifest, _ = read_checkpoint(h.directory, snapshot)
    assert report["paused"] and report["state"] == "INTERRUPTED" and report["outcome"] is None
    assert report["artifacts_complete"] and len(model.calls) == 3
    assert snapshot.run["segment_open"] == 0 and snapshot.run["last_checkpoint_id"] == 4
    assert manifest["counters"] == {"steps_used": 3, "tool_calls_admitted": 3}
    assert manifest["deadline_at"] == snapshot.events[0]["payload"]["deadline_at"]
    assert (h.resources.workspace / "repair/src/stats.cpp").read_text().find("samples.front()") >= 0
    assert not any(p.is_dir() for p in (h.resources.workspace / "snapshots").glob("*"))
    assert not any(e["type"] == "agent_stopped" for e in snapshot.events)
    assert not any(
        e["type"] == "verification_finished"
        and e["payload"].get("evaluation_role") == "independent"
        for e in snapshot.events
    )
    lock = RunLock(h.directory)
    lock.close()
    config = json.loads((h.directory / "execution-config.json").read_text())
    assert EvidenceRef(**config["script"]).read(h.directory, limit=256000) == source


@pytest.mark.sdk
def test_pause_native_items_include_whole_tool_batch_and_opaque_continuation(task, tmp_path):
    from agents.testing import ModelStep, ScriptedModel, assistant_message, function_call
    from openai.types.responses import ResponseReasoningItem

    model = ScriptedModel(
        [
            ModelStep(
                output=[
                    ResponseReasoningItem(
                        id="opaque",
                        type="reasoning",
                        summary=[],
                        encrypted_content="opaque-synthetic",
                    ),
                    function_call("read_file", {"path": "src/stats.cpp"}, call_id="first"),
                    function_call("read_file", {"path": "src/stats.hpp"}, call_id="second"),
                ]
            ),
            ModelStep(output=[assistant_message("未调用")]),
        ]
    )
    h = Harness(
        task, model, tmp_path / "runs", sandbox_factory=SimulatedSandbox, pause_after_step=1
    )
    r = h.run()
    snapshot = read_events(h.directory, h.directory.name)
    manifest, _ = read_checkpoint(h.directory, snapshot)
    native = json.loads(
        EvidenceRef(**manifest["native_next_input"]).read(h.directory, limit=256001)
    )
    assert r["paused"] and len(model.calls) == 1 and r["agent"]["tool_calls_used"] == 2
    assert any(item.get("encrypted_content") == "opaque-synthetic" for item in native["input"])
    assert [
        item["call_id"] for item in native["input"] if item.get("type") == "function_call_output"
    ] == ["first", "second"]
    assert "opaque-synthetic" not in (h.directory / "report.md").read_text()
    assert manifest["patch"]["size_bytes"] == 0


@pytest.mark.sdk
def test_normal_final_response_does_not_manufacture_a_pause_boundary(task, tmp_path):
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
    r = Harness(
        task, model, tmp_path / "runs", sandbox_factory=SimulatedSandbox, pause_after_step=2
    ).run()
    assert r["outcome"] == "ACCEPTED" and not r.get("paused") and len(model.calls) == 2


@pytest.mark.sdk
@pytest.mark.parametrize("failure", ["fsync", "transaction"])
def test_checkpoint_failure_leaves_orphan_and_never_returns_paused_success(
    task, tmp_path, monkeypatch, failure
):
    import repropatch.recovery as recovery
    from repropatch.events import EventLog

    if failure == "fsync":
        original = recovery._sync_directory

        def broken(path):
            if path.name == "2":
                raise OSError("注入目录持久化失败")
            return original(path)

        monkeypatch.setattr(recovery, "_sync_directory", broken)
    else:
        original = EventLog.__init__

        def broken(self, *args, **kwargs):
            original(self, *args, **kwargs)
            self.db.execute(
                "CREATE TRIGGER reject_cp BEFORE INSERT ON events "
                "WHEN NEW.type='checkpoint_committed' AND EXISTS (SELECT 1 FROM checkpoints) "
                "BEGIN SELECT RAISE(ABORT,'拒绝'); END"
            )
            self.db.commit()

        monkeypatch.setattr(EventLog, "__init__", broken)
    model = scripted(
        [{"tool": "read_file", "arguments": {"path": "src/stats.cpp"}}, {"finish": "未调用"}]
    )
    h = Harness(
        task, model, tmp_path / "runs", sandbox_factory=SimulatedSandbox, pause_after_step=1
    )
    r = h.run()
    snapshot = read_events(h.directory, h.directory.name)
    assert r["outcome"] == "ERROR" and not r.get("paused") and len(model.calls) == 1
    assert snapshot.run["last_checkpoint_id"] == 1 and snapshot.run["segment_open"] == 1
    assert (h.directory / "checkpoints/2/manifest.json").is_file()
    assert read_checkpoint(h.directory, snapshot)[0]["step_id"] == 0


@pytest.mark.sdk
def test_process_exit_between_durable_files_and_checkpoint_commit(task, tmp_path):
    code = """
import json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
from conftest import SimulatedSandbox
from repropatch.events import EventLog
from repropatch.harness import Harness
from repropatch.models import load_sdk_script
from repropatch.task import Task
original=EventLog.emit
def interrupted(self,kind,payload,**kwargs):
    if kind=='checkpoint_committed' and payload['checkpoint_id']==2: os._exit(73)
    return original(self,kind,payload,**kwargs)
EventLog.emit=interrupted
model=load_sdk_script(Path('examples/models/fix-negative-maximum.json'))
Harness(Task.from_dict(json.loads(sys.argv[1]),Path(sys.argv[2])),model,Path(sys.argv[3]),sandbox_factory=SimulatedSandbox,pause_after_step=1).run()
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            json.dumps(task.to_dict()),
            str(tmp_path),
            str(tmp_path / "runs"),
        ],
        capture_output=True,
        timeout=30,
        cwd=ROOT,
    )
    assert result.returncode == 73, result.stderr
    (root,) = (tmp_path / "runs").iterdir()
    snapshot = read_events(root, root.name)
    assert snapshot.run["state"] == "REPAIRING" and snapshot.run["segment_open"] == 1
    assert snapshot.run["steps_used"] == 1 and len(snapshot.checkpoints) == 1
    assert (root / "checkpoints/2/manifest.json").is_file()
    assert read_checkpoint(root, snapshot)[0]["step_id"] == 0


@pytest.mark.sdk
@pytest.mark.parametrize("failed", ["events.jsonl", "report.json"])
def test_pause_export_failure_keeps_authority_and_core_reexport(
    task, tmp_path, monkeypatch, failed, capsys
):
    original = AuditBudget.write

    def broken(self, name, content, **kwargs):
        if name == failed:
            raise OSError("注入导出失败")
        return original(self, name, content, **kwargs)

    monkeypatch.setattr(AuditBudget, "write", broken)
    h = Harness(
        task,
        scripted(
            [{"tool": "read_file", "arguments": {"path": "src/stats.cpp"}}, {"finish": "未调用"}]
        ),
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        pause_after_step=1,
    )
    r = h.run()
    before = (h.directory / "events.sqlite3").read_bytes()
    assert r["paused"] and r["outcome"] is None and r["command_error"] == "ARTIFACT_EXPORT_FAILED"
    monkeypatch.setattr(AuditBudget, "write", original)
    for name in ("report.json", "report.md", "events.jsonl", "run.json"):
        (h.directory / name).unlink(missing_ok=True)
    for name in ("agents", "openai", "repropatch.models"):
        monkeypatch.setitem(sys.modules, name, None)
    assert (
        main(["report", h.directory.name, "--root", str(h.directory.parent), "--format", "json"])
        == 0
    )
    assert json.loads(capsys.readouterr().out)["paused"]
    assert inspect_run(h.directory)["artifacts_complete"]
    assert (h.directory / "events.sqlite3").read_bytes() == before


@pytest.mark.sdk
def test_user_cancel_after_checkpoint_commit_is_terminal_cancellation(task, tmp_path, monkeypatch):
    import repropatch.recovery as recovery

    original = recovery.save_checkpoint

    def interrupted(*args):
        result = original(*args)
        if result[2]:
            raise KeyboardInterrupt()
        return result

    monkeypatch.setattr(recovery, "save_checkpoint", interrupted)
    h = Harness(
        task,
        scripted(
            [{"tool": "read_file", "arguments": {"path": "src/stats.cpp"}}, {"finish": "未调用"}]
        ),
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        pause_after_step=1,
    )
    r = h.run()
    assert r["outcome"] == "CANCELLED" and not r.get("paused") and r["independent"] is None
    assert read_events(h.directory, h.directory.name).run["state"] == "FINISHED"


@pytest.mark.sdk
def test_checkpoint_corruption_after_commit_cannot_report_successful_pause(
    task, tmp_path, monkeypatch, capsys
):
    import repropatch.recovery as recovery

    original = recovery.save_checkpoint

    def corrupted(harness, *args):
        result = original(harness, *args)
        if result[2]:
            path = harness.directory / result[0]["native_next_input"]["path"]
            path.write_bytes(path.read_bytes() + b"changed")
        return result

    monkeypatch.setattr(recovery, "save_checkpoint", corrupted)
    model = scripted(
        [{"tool": "read_file", "arguments": {"path": "src/stats.cpp"}}, {"finish": "未调用"}]
    )
    h = Harness(
        task, model, tmp_path / "runs", sandbox_factory=SimulatedSandbox, pause_after_step=1
    )
    report = h.run()
    assert (
        report["paused"]
        and report["outcome"] is None
        and report["command_error"] == "CHECKPOINT_CORRUPT"
    )
    assert not report["artifacts_complete"] and len(model.calls) == 1
    monkeypatch.setattr(Harness, "run", lambda self: report)
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(task.to_dict()))
    assert (
        main(
            [
                "run",
                str(task_path),
                "--mock-script",
                str(ROOT / "examples/models/fix-negative-maximum.json"),
                "--pause-after-step",
                "1",
                "--json",
            ]
        )
        == 3
    )
    assert "CHECKPOINT_CORRUPT" in capsys.readouterr().err
