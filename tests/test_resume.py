"""有限恢复的源码、输入、预算与未知副作用边界。"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import replace

import pytest
from conftest import ROOT, SimulatedSandbox

from repropatch.artifacts import EvidenceRef
from repropatch.errors import InfrastructureError, StateWriteError
from repropatch.events import read_events
from repropatch.harness import Harness
from repropatch.models import load_sdk_script
from repropatch.recovery import read_checkpoint, resume_run
from repropatch.reports import inspect_run
from repropatch.resources import RunLock
from repropatch.verification import RunClock

pytestmark = pytest.mark.sdk


@pytest.fixture(autouse=True)
def recovery_gate_runs(request, tmp_path):
    """显式恢复 gate 用 JUnit 属性关联本用例的真实 Run，不新增产品故障接口。"""
    yield
    if os.environ.get("REPROPATCH_RECOVERY_GATE") == "1":
        paths = sorted(
            str(path.parent)
            for path in tmp_path.rglob("events.sqlite3")
            if (path.parent / "report.json").is_file()
        )
        request.node.user_properties.append(("recovery_runs", json.dumps(paths)))


def paused_run(task, tmp_path, *, step=3, script=None):
    source = (ROOT / "examples/models/fix-negative-maximum.json").read_bytes()
    if script is not None:
        source = json.dumps(script).encode()
    path = tmp_path / "script.json"
    path.write_bytes(source)
    model = load_sdk_script(path)
    h = Harness(
        task,
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        pause_after_step=step,
        script_source=source,
    )
    r = h.run()
    assert r["paused"] and r["artifacts_complete"]
    return h, model


def test_resume_preserves_native_input_counters_and_uses_remaining_script(
    task, tmp_path, monkeypatch
):
    h, model = paused_run(task, tmp_path)
    before = read_events(h.directory, h.directory.name)
    manifest, _ = read_checkpoint(h.directory, before)
    native = json.loads(
        EvidenceRef(**manifest["native_next_input"]).read(h.directory, limit=256001)
    )
    import repropatch.agent_runtime as runtime

    original = runtime.run_sdk
    observed = []

    async def capture(**kwargs):
        observed.append((kwargs["input_items"], kwargs["instructions"], kwargs["max_turns"]))
        return await original(**kwargs)

    monkeypatch.setattr(runtime, "run_sdk", capture)
    r = resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    after = read_events(h.directory, h.directory.name)
    assert r["outcome"] == "ACCEPTED" and r["artifacts_complete"]
    assert len(model.calls) == 3
    assert observed == [(native["input"], native["instructions"], task.max_steps - 3)]
    assert after.run["steps_used"] == 5 and after.run["tool_calls_admitted"] == 4
    assert (
        after.run["recovery_attempt"] == 1 and after.run["deadline_at"] == before.run["deadline_at"]
    )
    assert r["usage"]["unknown_turns"] == 5
    # 恢复后的工具提示使用累计扣减，最后一次自检保留真实候选状态。
    tool_results = sorted((h.directory / "agent/tool-results").glob("*.json"))
    last_progress = json.loads(tool_results[-1].read_text())["progress"]
    assert last_progress["model_steps_remaining"] == task.max_steps - 4
    assert last_progress["tool_calls_remaining"] == task.budget.max_tool_calls - 4
    assert last_progress["source_changed"] is True
    assert len([e for e in after.events if e["type"] == "baseline_finished"]) == 1
    edits = [
        e
        for e in after.events
        if e["type"] == "tool_started" and e["payload"]["name"] == "edit_file"
    ]
    assert len(edits) == 1
    assert inspect_run(h.directory)["artifacts_complete"]
    RunLock(h.directory).close()


def test_resume_can_pause_again_at_absolute_turn_without_sticky_preference(task, tmp_path):
    h, _ = paused_run(task, tmp_path, step=1)
    second = resume_run(h.directory, pause_after_step=4, sandbox_factory=SimulatedSandbox)
    assert second["paused"] and second["agent"]["steps_used"] == 4
    final = resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    assert final["outcome"] == "ACCEPTED" and final["agent"]["steps_used"] == 5
    assert [item["evaluation_role"] for item in final["evaluations"]] == [
        "baseline",
        "agent_check",
        "independent",
    ]
    assert read_events(h.directory, h.directory.name).run["recovery_attempt"] == 2


def test_missing_disposable_workspace_is_rebuilt_from_complete_checkpoint(task, tmp_path):
    h, _ = paused_run(task, tmp_path)
    for work in h.resources.worktrees:
        work.close()
    shutil.rmtree(h.resources.workspace)
    r = resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    assert r["outcome"] == "ACCEPTED" and r["artifacts_complete"]


@pytest.mark.parametrize("change", ["source", "checkpoint", "implementation", "tools"])
def test_resume_rejects_divergence_without_model_or_overwriting_source(
    task, tmp_path, monkeypatch, change
):
    h, _ = paused_run(task, tmp_path)
    path = h.resources.workspace / "repair/src/stats.cpp"
    if change == "source":
        path.write_bytes(path.read_bytes() + b"\n// third party\n")
    elif change == "checkpoint":
        manifest, _ = read_checkpoint(h.directory)
        target = h.directory / manifest["native_next_input"]["path"]
        target.write_bytes(target.read_bytes() + b"changed")
    elif change == "implementation":
        monkeypatch.setattr("repropatch.harness.implementation_sha256", lambda: "0" * 64)
    else:
        monkeypatch.setattr("repropatch.tools.sdk_tools_sha256", lambda: "0" * 64)
    before = path.read_bytes()

    async def forbidden(**kwargs):
        pytest.fail("不安全恢复不能调用模型")

    monkeypatch.setattr("repropatch.agent_runtime.run_sdk", forbidden)
    r = resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    assert r["outcome"] == "RECOVERY_FAILED"
    expected = {
        "source": "WORKSPACE_DIVERGED",
        "checkpoint": "CHECKPOINT_CORRUPT",
        "implementation": "INPUT_CHANGED",
        "tools": "INPUT_CHANGED",
    }[change]
    assert r["reason_code"] == expected
    assert path.read_bytes() == before and r["agent"]["steps_used"] == 3
    assert r["verification_eligible"] is False
    assert r["diagnostics"]


@pytest.mark.parametrize("mode", ["turn", "tool", "agent_deadline", "wall_deadline"])
def test_resume_budget_does_not_refund_and_verifies_only_with_remaining_time(
    task, tmp_path, monkeypatch, mode
):
    budget = replace(
        task.budget,
        **({"max_steps": 4} if mode == "turn" else {"max_tool_calls": 3} if mode == "tool" else {}),
    )
    task = replace(task, budget=budget)
    h, _ = paused_run(task, tmp_path)
    if "deadline" in mode:
        original = RunClock.restore.__func__

        def expired(cls, *args):
            clock = original(cls, *args)
            clock.started -= (
                clock.remaining("independent" if mode == "wall_deadline" else "agent_check") + 1
            )
            return clock

        monkeypatch.setattr(RunClock, "restore", classmethod(expired))
    r = resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    assert r["outcome"] == ("INCONCLUSIVE" if mode == "wall_deadline" else "ACCEPTED")
    assert r["agent"]["steps_used"] == (4 if mode in {"turn", "tool"} else 3)
    assert r["agent"]["tool_calls_used"] == (4 if mode == "turn" else 3)
    assert r["agent"]["agent_stop_reason"] in {"STEP_BUDGET", "TOOL_BUDGET", "AGENT_DEADLINE"}
    assert r["engine"]["versions"] == {"openai-agents": "0.24.0", "openai": "3.35.1"}
    if mode == "wall_deadline":
        assert (h.directory / "patch.diff").read_bytes()
        assert r["independent"] is None or not r["independent"]["successful"]


@pytest.mark.parametrize("step", [0, 3, 12])
def test_invalid_pause_or_terminal_resume_never_changes_database(task, tmp_path, step):
    h, _ = paused_run(task, tmp_path)
    before = (h.directory / "events.sqlite3").read_bytes()
    with pytest.raises(Exception, match="PAUSE_STEP_INVALID"):
        resume_run(h.directory, pause_after_step=step, sandbox_factory=SimulatedSandbox)
    assert (h.directory / "events.sqlite3").read_bytes() == before
    r = resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    assert r["outcome"] == "ACCEPTED"
    terminal = (h.directory / "events.sqlite3").read_bytes()
    with pytest.raises(Exception, match="RUN_FINISHED"):
        resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    assert (h.directory / "events.sqlite3").read_bytes() == terminal


@pytest.mark.parametrize(
    "boundary",
    [
        "model_started",
        "model_finished",
        "edit_finished",
        "closed_checkpoint",
        "final_response",
        "checkpoint_files",
        "model_started_cleanup",
    ],
)
def test_process_death_only_resumes_closed_checkpoint(task, tmp_path, boundary, monkeypatch):
    from conftest import SimulatedSandbox

    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(task.to_dict()))
    code = """
import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/"tests"))
from conftest import SimulatedSandbox
from repropatch.events import EventLog
from repropatch.harness import Harness
from repropatch.models import load_sdk_script
from repropatch.task import Task
import repropatch.recovery as recovery
mode=sys.argv[3]
if mode=="model_started_cleanup":mode="model_started"
original=EventLog.emit
def emit(self,kind,payload,**kwargs):
    result=original(self,kind,payload,**kwargs)
    if mode=="checkpoint_files" and kind=="checkpoint_committed" and payload["step_id"]==3:
        os._exit(73)
    if ((mode in {"model_started","model_finished"} and kind==mode)
        or (mode=="final_response" and kind=="model_finished" and payload["step"]==5)
        or (mode=="edit_finished" and kind=="tool_finished" and payload["name"]=="edit_file")):
        os._exit(73)
    return result
EventLog.emit=emit
save=recovery.save_checkpoint
def checkpoint(h,*args):
    result=save(h,*args)
    if mode=="closed_checkpoint" and result[0]["step_id"]==3:os._exit(73)
    return result
recovery.save_checkpoint=checkpoint
model,source=load_sdk_script(Path(sys.argv[1])/"examples/models/fix-negative-maximum.json",with_source=True)
Harness(Task.load(Path(sys.argv[2])),model,sandbox_factory=SimulatedSandbox,script_source=source).run()
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            str(ROOT),
            str(task_path),
            boundary,
        ],
        capture_output=True,
        timeout=40,
    )
    assert result.returncode == 73, result.stderr.decode()
    (directory,) = task.output_root.iterdir()
    before = read_events(directory, directory.name)
    if boundary == "model_started_cleanup":

        def uncertain(resources):
            resources.cleanup_errors.append("OWNED_RESOURCE_UNCONFIRMED")
            raise InfrastructureError("OWNED_RESOURCE_UNCONFIRMED: 清理状态未知")

        monkeypatch.setattr("repropatch.recovery._cleanup_owned", uncertain)
    report = resume_run(directory, sandbox_factory=SimulatedSandbox)
    if boundary == "closed_checkpoint":
        assert report["outcome"] == "ACCEPTED" and report["agent"]["steps_used"] == 5
    else:
        assert report["outcome"] == "RECOVERY_FAILED"
        assert report["reason_code"] == (
            "MODEL_RESULT_UNKNOWN" if boundary.startswith("model_started") else "OPEN_AGENT_SEGMENT"
        )
        assert report["agent"]["steps_used"] == before.run["steps_used"]
        after = read_events(directory, directory.name)
        assert (
            len([e for e in after.events if e["type"] == "model_started"])
            == before.run["steps_used"]
        )
        if boundary == "model_started_cleanup":
            assert not report["cleanup"]["active_code_stopped"] and report["cleanup"]["errors"]


@pytest.mark.parametrize("partial", [False, True])
def test_resume_known_and_unknown_usage_accumulates_across_pause(task, tmp_path, partial):
    script = json.loads((ROOT / "examples/models/fix-negative-maximum.json").read_text())
    for step in script["steps"]:
        step["usage"] = {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12}
    if partial:
        script["steps"][0]["usage"] = {"input_tokens": 10}
    h, _ = paused_run(task, tmp_path, script=script)
    r = resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    assert r["outcome"] == "ACCEPTED"
    assert r["usage"] == {
        "synthetic": True,
        "input_tokens": 50,
        "output_tokens": None if partial else 10,
        "total_tokens": None if partial else 60,
        "unknown_turns": 1 if partial else 0,
        "known_tokens": {
            "input_tokens": 50,
            "output_tokens": 8 if partial else 10,
            "total_tokens": 48 if partial else 60,
        },
    }


def test_orphan_next_directory_is_preserved_without_becoming_recovery_input(task, tmp_path):
    h, _ = paused_run(task, tmp_path)
    snapshot = read_events(h.directory, h.directory.name)
    orphan = h.directory / "checkpoints" / str(snapshot.run["last_checkpoint_id"] + 1)
    orphan.mkdir(mode=0o700)
    (orphan / "partial.json").write_text("not a committed checkpoint")
    (orphan / "partial.json").chmod(0o600)
    r = resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    assert r["outcome"] == "ACCEPTED"
    assert (
        h.directory / "recovery/1/orphan-checkpoint/partial.json"
    ).read_text() == "not a committed checkpoint"


def test_recovery_transaction_failure_keeps_database_and_writes_separate_receipt(task, tmp_path):
    h, _ = paused_run(task, tmp_path)
    dbpath = h.directory / "events.sqlite3"
    with sqlite3.connect(dbpath) as db:
        db.execute(
            "CREATE TRIGGER reject_recovery BEFORE UPDATE OF state ON runs "
            "WHEN NEW.state='RECOVERING' BEGIN SELECT RAISE(ABORT,'拒绝恢复'); END"
        )
    before = dbpath.read_bytes()
    with pytest.raises(StateWriteError, match="STATE_WRITE_FAILED"):
        resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    assert dbpath.read_bytes() == before
    receipt = json.loads((h.directory / "recovery-error.json").read_text())
    assert receipt["database_updated"] is False
    assert read_events(h.directory, h.directory.name).run["state"] == "INTERRUPTED"


def test_recovery_cancel_is_terminal_cancel_and_never_a_pause(task, tmp_path, monkeypatch):
    h, _ = paused_run(task, tmp_path)

    def cancel(*args):
        raise KeyboardInterrupt()

    monkeypatch.setattr("repropatch.recovery._resume_harness", cancel)
    r = resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    assert r["outcome"] == "CANCELLED" and r["state"] == "FINISHED" and not r["paused"]
    assert r["agent"]["steps_used"] == 3 and r["artifacts_complete"]


def test_sdk_version_change_cannot_resume_same_run(task, tmp_path, monkeypatch):
    from importlib import metadata

    h, _ = paused_run(task, tmp_path)
    original = metadata.version
    monkeypatch.setattr(
        metadata, "version", lambda name: "0.0.0" if name == "openai-agents" else original(name)
    )
    r = resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    assert r["outcome"] == "RECOVERY_FAILED" and r["reason_code"] == "INPUT_CHANGED"


def test_active_writer_cannot_be_taken_over(task, tmp_path):
    h, _ = paused_run(task, tmp_path)
    before = (h.directory / "events.sqlite3").read_bytes()
    lock = RunLock(h.directory)
    try:
        with pytest.raises(BlockingIOError):
            resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    finally:
        lock.close()
    assert (h.directory / "events.sqlite3").read_bytes() == before
    h.directory.chmod(0o755)
    try:
        with pytest.raises(InfrastructureError, match="RUN_OWNERSHIP"):
            resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    finally:
        h.directory.chmod(0o700)
    assert (h.directory / "events.sqlite3").read_bytes() == before


def test_uncertain_cleanup_refuses_safe_candidate_without_model_call(task, tmp_path, monkeypatch):
    h, _ = paused_run(task, tmp_path)

    def uncertain(resources):
        resources.cleanup_errors.append("OWNED_RESOURCE_UNCONFIRMED")
        raise InfrastructureError("OWNED_RESOURCE_UNCONFIRMED: daemon 不可达")

    monkeypatch.setattr("repropatch.recovery._cleanup_owned", uncertain)
    r = resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    assert r["outcome"] == "RECOVERY_FAILED" and r["reason_code"] == "OWNED_RESOURCE_UNCONFIRMED"
    assert r["agent"]["steps_used"] == 3 and not r["cleanup"]["active_code_stopped"]


def test_resume_native_items_preserve_opaque_continuation_and_whole_batch(task, tmp_path):
    script = json.loads((ROOT / "examples/models/fix-negative-maximum.json").read_text())
    script["steps"][0]["output"] = [
        {
            "type": "reasoning",
            "id": "synthetic-opaque",
            "summary": [],
            "encrypted_content": "opaque-synthetic-continuation",
        },
        *script["steps"][0]["output"],
        *script["steps"][1]["output"],
    ]
    del script["steps"][1]
    h, _ = paused_run(task, tmp_path, step=2, script=script)
    manifest, _ = read_checkpoint(h.directory)
    native = json.loads(
        EvidenceRef(**manifest["native_next_input"]).read(h.directory, limit=256001)
    )
    assert any(
        item.get("encrypted_content") == "opaque-synthetic-continuation" for item in native["input"]
    )
    outputs = [
        item["call_id"] for item in native["input"] if item.get("type") == "function_call_output"
    ]
    assert outputs == ["call-0", "call-1", "call-2"]
    r = resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    assert r["outcome"] == "ACCEPTED" and r["agent"]["steps_used"] == 4
    assert r["agent"]["tool_calls_used"] == 4
    assert "opaque-synthetic-continuation" not in (h.directory / "report.md").read_text()


def test_process_death_during_recovery_does_not_repeat_reconstruction(task, tmp_path):
    h, _ = paused_run(task, tmp_path)
    code = """
import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/"tests"))
from conftest import SimulatedSandbox
import repropatch.recovery as recovery
def stop(*args):os._exit(73)
recovery._resume_harness=stop
recovery.resume_run(Path(sys.argv[2]),sandbox_factory=SimulatedSandbox)
"""
    child = subprocess.run(
        [sys.executable, "-c", code, str(ROOT), str(h.directory)], capture_output=True, timeout=20
    )
    assert child.returncode == 73, child.stderr.decode()
    assert read_events(h.directory, h.directory.name).run["state"] == "RECOVERING"
    r = resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    assert r["outcome"] == "RECOVERY_FAILED" and r["reason_code"] == "UNSUPPORTED_RECOVERY_PHASE"
    assert r["agent"]["steps_used"] == 3
    assert read_events(h.directory, h.directory.name).run["recovery_attempt"] == 2


def test_expired_agent_without_candidate_does_not_call_model_or_verify(task, tmp_path, monkeypatch):
    h, model = paused_run(task, tmp_path, step=1)
    original = RunClock.remaining

    def expired(self, role):
        return -1 if role == "agent_check" else original(self, role)

    monkeypatch.setattr(RunClock, "remaining", expired)
    report = resume_run(h.directory, sandbox_factory=SimulatedSandbox)
    assert report["outcome"] == "BUDGET_EXHAUSTED" and report["reason_code"] == "AGENT_DEADLINE"
    assert report["agent"]["steps_used"] == 1 and len(model.calls) == 1
    assert report["independent"] is None and report["candidate"] is None
