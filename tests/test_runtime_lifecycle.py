"""执行预算、原始日志、所属资源及失败保留的行为验收。"""

import json
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import SimulatedSandbox, scripted

from repropatch.artifacts import AuditBudget, EvidenceRef
from repropatch.errors import AuditLimit, CleanupUnconfirmed, InfrastructureError, SourceChanged
from repropatch.events import EventLog
from repropatch.harness import Harness
from repropatch.process import RAW_OUTPUT_LIMIT, run_logged_process
from repropatch.resources import RunLock, RunResources
from repropatch.sandbox import DockerSandbox


def logged(tmp_path, script, **kwargs):
    return run_logged_process(
        [sys.executable, "-c", script],
        root=tmp_path,
        budget=AuditBudget(tmp_path),
        timeout=3,
        **kwargs,
    )


@pytest.mark.parametrize("mode", ["stdout", "stderr", "both"])
def test_raw_limit_exactly_reached_stops_immediately(tmp_path, mode):
    count = RAW_OUTPUT_LIMIT // (2 if mode == "both" else 1)
    script = "import sys,time; "
    for stream in ("stdout", "stderr") if mode == "both" else (mode,):
        script += f"sys.{stream}.buffer.write(b'x'*{count}); sys.{stream}.flush(); "
    script += "time.sleep(30)"
    reasons = []
    result = logged(tmp_path, script, on_stop=reasons.append)
    assert result.status == "output_limit" and not result.ok and result.output_truncated
    assert result.duration_seconds < 2
    assert reasons == ["output_limit"]
    sizes = [
        len(ref.read(tmp_path, limit=RAW_OUTPUT_LIMIT))
        for ref in (result.stdout_log, result.stderr_log)
    ]
    assert sum(sizes) == RAW_OUTPUT_LIMIT
    assert sum(sizes) == result.stdout_bytes + result.stderr_bytes


def test_raw_logs_preserve_binary_empty_streams_and_middle_signature(tmp_path):
    script = (
        "import sys; sys.stdout.buffer.write(b'head'+b'x'*100000+b'MARKER'"
        "+b'x'*100000+b'tail\\xff\\x1b')"
    )
    result = logged(tmp_path, script)
    assert result.ok and result.truncated and not result.output_truncated
    assert len(result.output.encode()) <= 65536
    assert "MARKER" not in result.stdout and result.contains("MARKER", tmp_path)
    from repropatch.tools import Toolbox, model_command

    view = Toolbox(
        None, (), lambda name: {"commands": [model_command(result.to_dict())]}, readable=()
    ).run_command("verify")["commands"][0]
    assert "output" not in view
    assert len((view["stdout"] + view["stderr"]).encode("utf-8")) <= 65536
    assert "head" in result.stdout and "tail" in result.stdout and "\\x1b" in result.stdout
    assert "\x1b" not in result.stdout
    assert result.stdout_log.read(tmp_path, limit=RAW_OUTPUT_LIMIT).endswith(b"tail\xff\x1b")
    assert result.stderr_log.read(tmp_path, limit=RAW_OUTPUT_LIMIT) == b""
    for ref in (result.stdout_log, result.stderr_log):
        assert (tmp_path / ref.path).stat().st_mode & 0o777 == 0o600


def test_failure_signature_cannot_join_stdout_and_stderr(tmp_path):
    result = logged(
        tmp_path, "import sys; print('first',end=''); print('second',end='',file=sys.stderr)"
    )
    assert result.output == "firstsecond"
    assert not result.contains("firstsecond", tmp_path)
    assert result.contains("first", tmp_path) and result.contains("second", tmp_path)
    (tmp_path / result.stdout_log.path).write_bytes(b"corrupt")
    with pytest.raises(InfrastructureError, match="ARTIFACT_CORRUPT"):
        result.contains("first", tmp_path)


def test_log_files_exist_on_launch_failure_and_budget_prevents_launch(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise FileNotFoundError("missing executable")

    monkeypatch.setattr("repropatch.process.subprocess.Popen", forbidden)
    result = logged(tmp_path, "print('never')")
    assert result.status == "infra_error" and result.returncode is None
    assert result.stdout_log.read(tmp_path, limit=1) == b""
    assert result.stderr_log.read(tmp_path, limit=1) == b""
    other = tmp_path / "small"
    other.mkdir()
    result = run_logged_process(
        ["never"], root=other, budget=AuditBudget(other, limit=65536), timeout=1
    )
    assert result.status == "infra_error" and "AUDIT_LIMIT" in result.error
    assert result.stdout_log is None and result.stderr_log is None


def test_audit_budget_preserves_earlier_evidence_and_final_reserve(tmp_path):
    budget = AuditBudget(tmp_path, limit=1024 * 1024, reserve=64 * 1024)
    ref = EvidenceRef.save(tmp_path, "earlier.bin", b"x" * 900000, budget=budget)
    with pytest.raises(AuditLimit):
        budget.write("overflow.bin", b"x" * 100000)
    budget.write("final.json", b'{"status":"error"}', emergency=True)
    assert budget.usage() <= budget.limit and ref.read(tmp_path, limit=1000000) == b"x" * 900000
    assert not (tmp_path / "overflow.bin").exists()


def test_event_budget_does_not_commit_rejected_payload(tmp_path):
    budget = AuditBudget(tmp_path, limit=512 * 1024)
    log = EventLog(tmp_path, "a" * 32, budget=budget)
    from conftest import created_payload

    log.emit("run_created", created_payload())
    with pytest.raises(AuditLimit):
        log.emit("inputs_frozen", {"data": "x" * 150000})
    log.emit("cleanup_finished", {"status": "error"}, emergency=True)
    log.close()
    with sqlite3.connect(tmp_path / "events.sqlite3") as db:
        assert db.execute("SELECT type FROM events ORDER BY seq").fetchall() == [
            ("run_created",),
            ("cleanup_finished",),
        ]
    assert budget.usage() < budget.limit


def test_run_lock_is_a_live_descriptor_and_directory_collision_is_rejected(tmp_path):
    resources = RunResources(tmp_path / "out", tmp_path / "work", "run", tmp_path, "a" * 40)
    assert resources.directory.stat().st_mode & 0o777 == 0o700
    assert resources.workspace.stat().st_mode & 0o777 == 0o700
    with pytest.raises(BlockingIOError):
        RunLock(resources.directory)
    with pytest.raises(FileExistsError):
        RunResources(tmp_path / "out", tmp_path / "work", "run", tmp_path, "a" * 40)
    resources.close()
    lock = RunLock(resources.directory)
    lock.close()


@pytest.mark.sdk
@pytest.mark.parametrize("retain", ["none", "on_failure", "always"])
@pytest.mark.parametrize("success", [True, False])
def test_harness_retention_keeps_only_repair_and_latest_snapshot(
    task, model, tmp_path, retain, success
):
    selected = model if success else scripted([{"finish": "done"}])
    report = Harness(
        replace(task, retain=retain), selected, tmp_path / "runs", sandbox_factory=SimulatedSandbox
    ).run()
    assert report["status"] == ("passed" if success else "no_patch"), report
    root = Path(report["workspace_directory"])
    keep = retain == "always" or (retain == "on_failure" and not success)
    assert (root / "repair").exists() is keep
    assert not (root / "validation").exists()
    snapshots = list((root / "snapshots").glob("*"))
    assert len(snapshots) == int(keep)
    if keep:
        assert snapshots[0].name.endswith("independent" if success else "baseline")
    audit = Path(report["artifact_directory"])
    assert not (audit / "snapshots").exists()
    for path in audit.rglob("*"):
        if path.is_file():
            assert path.stat().st_mode & 0o777 == 0o600
    assert report["cleanup_confirmed"] is True


def test_snapshot_cleanup_refuses_replaced_root(tmp_path):
    resources = RunResources(tmp_path / "out", tmp_path / "work", "run", tmp_path, "a" * 40)
    source = resources.workspace / "snapshots/one"
    source.mkdir(parents=True)
    (source / "a.cpp").write_text("x")
    from repropatch.workspace import source_manifest

    resources.register_snapshot(source, source_manifest(source))
    saved = source.with_name("saved")
    source.rename(saved)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    sentinel.write_bytes(b"keep")
    source.symlink_to(foreign, target_is_directory=True)
    with pytest.raises(SourceChanged):
        resources.finish_evaluation(source, keep=False)
    assert sentinel.read_bytes() == b"keep"
    resources.close()


@pytest.mark.parametrize("failure", ["missing-daemon", "still-exists", "wrong-label"])
def test_container_cleanup_does_not_confuse_unknown_with_absent(tmp_path, monkeypatch, failure):
    sandbox = DockerSandbox(tmp_path, "repropatch-cpp:0.1")
    sandbox.created = True
    sandbox.container_id = "a" * 64
    history = []
    actual = {
        "Id": sandbox.container_id,
        "Name": "/" + sandbox.name,
        "Config": {"Labels": sandbox.labels},
    }
    if failure == "wrong-label":
        actual["Config"]["Labels"] = {"repropatch.run": "someone-else"}

    def inspect(*args, **kwargs):
        if failure == "missing-daemon":
            raise InfrastructureError("daemon disconnected")
        return actual

    monkeypatch.setattr(sandbox, "_inspect", inspect)
    monkeypatch.setattr(sandbox, "_docker", lambda *args, **kwargs: history.append(args))
    with pytest.raises(CleanupUnconfirmed):
        sandbox.close()
    assert not sandbox.cleanup_confirmed
    assert bool(history) is (failure == "still-exists")


def test_daemon_error_is_not_missing_container(tmp_path, monkeypatch):
    from repropatch.process import CommandResult

    sandbox = DockerSandbox(tmp_path, "repropatch-cpp:0.1")
    monkeypatch.setattr(
        "repropatch.sandbox.run_process",
        lambda *a, **k: CommandResult(
            ("docker",),
            1,
            "Cannot connect to Docker daemon",
            0.01,
            stderr="Cannot connect to Docker daemon",
        ),
    )
    with pytest.raises(InfrastructureError, match="DOCKER_FAILED"):
        sandbox._inspect("a" * 64)


@pytest.mark.sdk
def test_harness_audit_limit_stops_before_model_and_writes_error(task, tmp_path, monkeypatch):
    monkeypatch.setattr("repropatch.artifacts.MAX_AUDIT_BYTES", 256 * 1024)

    class HugeBaseline(SimulatedSandbox):
        def run(self, argv):
            result = super().run(argv)
            return replace(result, output="x" * 100000)

    class ForbiddenModel:
        def complete(self, *args):
            pytest.fail("预算耗尽后不能调用模型")

    report = Harness(task, ForbiddenModel(), tmp_path / "runs", sandbox_factory=HugeBaseline).run()
    assert report["status"] == "error" and "AUDIT_LIMIT" in report["error"]
    root = Path(report["artifact_directory"])
    assert json.loads((root / "report.json").read_bytes())["status"] == "error"
    assert sum(p.stat().st_size for p in root.rglob("*") if p.is_file()) <= 256 * 1024


@pytest.mark.sdk
@pytest.mark.parametrize("phase", ["baseline", "independent"])
def test_harness_cleanup_failure_cannot_produce_success(task, model, tmp_path, phase):
    class Unconfirmed(SimulatedSandbox):
        def __exit__(self, *args):
            if self.source.name.endswith(phase):
                raise CleanupUnconfirmed("清理确认失败")

    report = Harness(task, model, tmp_path / "runs", sandbox_factory=Unconfirmed).run()
    assert report["outcome"] == "INCONCLUSIVE" and report["verified"] is False
    assert report["reason_code"] == "CLEANUP_UNCONFIRMED"
    if phase == "baseline":
        assert report["model_steps"] == 0 and len(report["evaluations"]) == 1
    assert report["evaluations"][-1]["phase"] == phase


@pytest.mark.parametrize("unsupported", ["volume", "cgroup"])
def test_unsupported_image_or_daemon_never_creates_container(tmp_path, monkeypatch, unsupported):
    from repropatch.process import CommandResult

    sandbox = DockerSandbox(tmp_path, "repropatch-cpp:0.1")
    calls = []

    def docker(*args, **kwargs):
        calls.append(args)
        if args[0] == "info":
            value = dict.fromkeys(("MemoryLimit", "SwapLimit", "CpuCfsQuota", "PidsLimit"), True)
            if unsupported == "cgroup":
                value["MemoryLimit"] = False
        elif args[0] == "image":
            value = [{"Id": "sha256:" + "a" * 64, "Config": {"Volumes": {"/extra": {}}}}]
        else:
            pytest.fail("不支持的镜像或 daemon 不能创建容器")
        return CommandResult(tuple(args), 0, json.dumps(value), 0.001)

    monkeypatch.setattr(sandbox, "_docker", docker)
    with pytest.raises(InfrastructureError):
        sandbox.__enter__()
    assert not sandbox.created


@pytest.mark.parametrize("oom", [False, True])
def test_exit_137_requires_docker_oom_evidence(tmp_path, monkeypatch, oom):
    from repropatch.process import CommandResult

    sandbox = DockerSandbox(tmp_path, "repropatch-cpp:0.1", log_root=tmp_path)
    sandbox.container_id = "a" * 64
    sandbox.active = True
    actual = {
        "Id": sandbox.container_id,
        "Name": "/" + sandbox.name,
        "Config": {"Labels": sandbox.labels},
        "State": {"Running": True, "OOMKilled": oom},
    }
    monkeypatch.setattr(sandbox, "_inspect", lambda *a, **k: actual)
    monkeypatch.setattr(
        "repropatch.sandbox.run_logged_process", lambda *a, **k: CommandResult(("x",), 137, "", 0.1)
    )

    def close():
        sandbox.active = False
        sandbox.cleanup_confirmed = True

    monkeypatch.setattr(sandbox, "close", close)
    result = sandbox.run(("x",))
    assert result.status == ("oom_killed" if oom else "exited")
    assert result.cleanup_confirmed is oom


@pytest.mark.sdk
def test_successful_diagnostic_snapshot_is_released_before_next_turn(task, tmp_path):
    actions = [
        {
            "tool": "edit_file",
            "arguments": {
                "path": "src/stats.cpp",
                "old": "int best = 0;",
                "new": "int best = samples.front();",
            },
        },
        {"tool": "run_command", "arguments": {"name": "verify"}},
        {"finish": "done"},
    ]

    from agents.testing import ModelStep, assistant_message

    def checked(call):
        roots = list(task.workspace_root.glob("*/snapshots"))
        assert len(roots) == 1
        assert [p.name for p in roots[0].iterdir()] == ["001-baseline"]
        return ModelStep(output=[assistant_message("完成")])

    selected = scripted(actions[:2])
    selected.enqueue(ModelStep(responder=checked))
    report = Harness(task, selected, tmp_path / "runs", sandbox_factory=SimulatedSandbox).run()
    assert report["status"] == "passed", report


def test_log_sync_failure_stops_execution_and_preserves_timeout_status(tmp_path, monkeypatch):
    from repropatch.process import RawResult

    def failed_sync(*args):
        raise OSError("模拟日志同步失败")

    reasons = []
    monkeypatch.setattr("repropatch.process.os.fsync", failed_sync)
    result = logged(tmp_path, "print('actual bytes')", on_stop=reasons.append)
    assert result.status == "infra_error" and not result.ok
    assert "LOG_IO" in result.error and reasons == ["infra_error"]
    assert result.stdout_log.read(tmp_path, limit=100) == b"actual bytes\n"

    def timeout(argv, **kwargs):
        kwargs["on_stop"]("timed_out")
        return RawResult(tuple(argv), -9, b"", b"", 0.01, timed_out=True, status="timed_out")

    monkeypatch.setattr("repropatch.process.run_process_bytes", timeout)
    result = logged(tmp_path, "unused", on_stop=reasons.append)
    assert result.status == "timed_out" and result.timed_out and not result.ok
    assert "LOG_IO" in result.error
    assert reasons == ["infra_error", "timed_out"]
