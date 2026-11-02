"""原生执行器的大型目录输入、启动错误反馈与零请求回归。"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import formal_benchmark as formal
import prepare_mini_environment as preparation
import run_benchmark_agent as worker
import run_codex_benchmark as codex
from benchmark_budget import BudgetLimit, LocalUsageLedger
from score_benchmark_attempt import producer_blocker

from repropatch.agent_runtime import model_file_scope
from repropatch.context import ContextPolicy
from repropatch.task import Task
from repropatch.workspace import git


@pytest.fixture
def native_inputs(task, tmp_path, monkeypatch):
    raw = task.to_dict()
    raw["budget"].update(
        max_steps=None, max_tool_calls=None, max_output_tokens=8192, model_timeout_seconds=180
    )
    task = Task.from_dict(raw, tmp_path)
    task_path = tmp_path / "task.yaml"
    task_path.write_bytes(task.source_bytes)
    mini = tmp_path / "mini-source"
    mini.mkdir()
    files = ("agents/default.py", "environments/docker.py", "models/test_models.py")
    for name in files:
        path = mini / "src/minisweagent" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# 固定源码预检样本。\n")
    git(mini, "init", "--template=", "-q")
    git(mini, "add", ".")
    git(mini, "-c", "user.name=Test", "-c", "user.email=test@localhost", "commit", "-qm", "fixture")
    commit = git(mini, "rev-parse", "HEAD").strip()
    monkeypatch.setattr(preparation, "MINI_COMMIT", commit)
    environment = tmp_path / "environment"
    environment.mkdir()
    source = environment / "source"
    shutil.copytree(task.repository, source)
    preparation.set_container_read_permissions(source)
    config = {"image": task.environment.image, "forward_env": [], "run_args": []}
    (environment / "environment.json").write_text(json.dumps(config))
    (environment / "preparation.json").write_text(
        json.dumps(
            {
                "mini_commit": commit,
                "base_commit": task.revision,
                "image_id": task.environment.image,
                "editable_files": sorted(task.editable_paths),
                "native_source_sha256": {
                    name: hashlib.sha256(
                        (mini / "src/minisweagent" / name).read_bytes()
                    ).hexdigest()
                    for name in files
                },
            }
        )
    )
    policy = ContextPolicy(compaction_enabled=False, request_cap=None, tool_output_max_bytes=1)
    readable = worker.task_readable_files(task)
    common = {
        "task": task.prompt,
        "base_commit": task.revision,
        "image_id": task.environment.image,
        "budget": asdict(task.budget),
        **model_file_scope(
            SimpleNamespace(readable_files=readable, editable_files=task.editable_paths), policy
        ),
    }
    common_path = tmp_path / "common-input.json"
    common_path.write_text(json.dumps({"input": [{"role": "user", "content": json.dumps(common)}]}))
    ledger = LocalUsageLedger.create_scoped(
        tmp_path / "ledger.sqlite3", {"fixture": None}, context_policy=policy
    )
    args = SimpleNamespace(
        task=task_path,
        mini_source=mini,
        mini_environment=environment / "environment.json",
        common_input=common_path,
        ledger=ledger.path,
        attempt="fixture",
        output=tmp_path / "attempt",
        agent_seconds=60,
        native_context=True,
        check_only=False,
    )
    return SimpleNamespace(task=task, args=args, ledger=ledger, common=common, readable=readable)


def write_common(inputs):
    inputs.args.common_input.write_text(
        json.dumps({"input": [{"role": "user", "content": json.dumps(inputs.common)}]})
    )


def arguments(inputs, agent, *, check_only=False):
    args = inputs.args
    values = [
        "worker.py",
        "--task",
        str(args.task),
        "--ledger",
        str(args.ledger),
        "--attempt",
        args.attempt,
        "--output",
        str(args.output),
        "--mini-source",
        str(args.mini_source),
        "--mini-environment",
        str(args.mini_environment),
        "--common-input",
        str(args.common_input),
        "--agent-seconds",
        str(args.agent_seconds),
        "--native-context",
    ]
    if agent == "mini":
        values += ["--agent", "mini", "--provider", "local-luna"]
    else:
        values += ["--binary", str(args.output.parent / "missing-codex")]
    return values + (["--check-only"] if check_only else [])


@pytest.mark.parametrize("representation", ["array", "discovery"])
def test_common_input_accepts_frozen_file_scope_without_rewriting(native_inputs, representation):
    inputs = native_inputs
    if representation == "array":
        inputs.common["readable"] = inputs.readable
        write_common(inputs)
    before = inputs.args.common_input.read_bytes()
    _, common, source = worker.mini_inputs(inputs.args, inputs.task, inputs.ledger.policy)
    assert common == json.loads(before)["input"][0]["content"]
    assert inputs.args.common_input.read_bytes() == before
    assert source == inputs.args.mini_environment.parent / "source"
    assert inputs.ledger.summary()["issued_requests"] == 0


@pytest.mark.parametrize("field", ["file_count", "roots", "source_root", "discovery_tool"])
def test_forged_discovery_scope_retains_identity_guard(native_inputs, field):
    inputs = native_inputs
    inputs.common["readable"][field] = {
        "file_count": len(inputs.readable) + 1,
        "roots": ["outside"],
        "source_root": "/outside",
        "discovery_tool": "other-tool",
    }[field]
    write_common(inputs)
    with pytest.raises(BudgetLimit, match="COMMON_TASK_MISMATCH"):
        worker.mini_inputs(inputs.args, inputs.task, inputs.ledger.policy)
    assert inputs.ledger.summary()["requests"] == 0


@pytest.mark.parametrize("agent", ["mini", pytest.param("codex", marks=pytest.mark.sdk)])
@pytest.mark.parametrize("check_only", [False, True])
def test_preflight_failure_preserves_original_error_and_zero_requests(
    native_inputs, monkeypatch, capsys, agent, check_only
):
    inputs = native_inputs
    inputs.common["readable"]["file_count"] += 1
    write_common(inputs)
    monkeypatch.setattr(sys, "argv", arguments(inputs, agent, check_only=check_only))
    monkeypatch.setattr(worker, "mini_agent", lambda *a: pytest.fail("预检后调用了模型入口"))
    monkeypatch.setattr(
        worker, "BudgetHooks", lambda *a, **k: pytest.fail("预检后创建了模型计量器")
    )
    assert (worker.main() if agent == "mini" else codex.main()) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["error_type"] == "BudgetLimit"
    assert result["error_code"] == result["error_message"] == "COMMON_TASK_MISMATCH"
    assert result["error_stage"] == "preflight"
    assert result["error_detail"] == {"mismatched_fields": ["readable"]}
    assert result["native_status"] == "ENVIRONMENT_ERROR"
    assert result["usage"]["issued_requests"] == inputs.ledger.summary()["issued_requests"] == 0
    assert result["task_sha256"] == hashlib.sha256(inputs.task.source_bytes).hexdigest()
    assert producer_blocker(result) == ("INFRASTRUCTURE_FAILED", "infrastructure")
    if check_only:
        assert not inputs.args.output.exists()
    else:
        assert json.loads((inputs.args.output / "result.json").read_text()) == result
        assert (inputs.args.output / "task.original.yaml").read_bytes() == inputs.task.source_bytes


def test_startup_subprocess_error_preserves_stderr_and_command(native_inputs, capsys):
    inputs = native_inputs
    error = subprocess.CalledProcessError(
        127, ["codex", "--version"], output=b"", stderr=b"loader: missing native dependency\n"
    )
    assert (
        worker.startup_failure(
            inputs.args, error, agent="codex", task=inputs.task, ledger=inputs.ledger
        )
        == 2
    )
    result = json.loads(capsys.readouterr().out)
    assert result["error_command"] == ["codex", "--version"]
    assert result["error_exit_code"] == 127
    assert result["error_stderr"] == "loader: missing native dependency\n"
    assert result["error_type"] == "CalledProcessError"
    assert result["usage"]["requests"] == 0


def test_startup_failure_preserves_existing_worker_result(native_inputs, capsys):
    inputs = native_inputs
    inputs.args.output.mkdir()
    original = b'{"existing":true}\n'
    (inputs.args.output / "result.json").write_bytes(original)
    worker.startup_failure(inputs.args, FileExistsError("attempt exists"), agent="mini")
    assert (inputs.args.output / "result.json").read_bytes() == original
    assert json.loads(capsys.readouterr().out)["error_message"] == "attempt exists"


@pytest.mark.sdk
@pytest.mark.parametrize("stage", ["worker_startup", "host_relay_startup"])
def test_codex_late_startup_failure_preserves_zero_request_result(
    native_inputs, monkeypatch, capsys, stage
):
    inputs = native_inputs
    binary = inputs.args.output.parent / "codex"
    binary.write_bytes(b"fixture")
    binary.with_name("codex-code-mode-host").write_bytes(b"fixture")
    check_output = subprocess.check_output

    def version(command, **kwargs):
        if command == [str(binary), "--version"]:
            return b"codex-cli 0.163.0\n"
        return check_output(command, **kwargs)

    monkeypatch.setattr(codex.subprocess, "check_output", version)
    monkeypatch.setattr(sys, "argv", [*arguments(inputs, "codex"), "--binary", str(binary)])
    if stage == "worker_startup":
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        message = "'OPENAI_API_KEY'"
    else:
        monkeypatch.setenv("OPENAI_API_KEY", "unused-offline-test")

        def bind(*args, **kwargs):
            raise OSError("AF_UNIX path too long")

        monkeypatch.setattr(codex.socketserver.UnixStreamServer, "__init__", bind)
        message = "AF_UNIX path too long"
    assert codex.main() == 2
    result = json.loads(capsys.readouterr().out)
    assert result["error_stage"] == stage
    assert result["error_message"] == message
    assert result["usage"]["issued_requests"] == inputs.ledger.summary()["issued_requests"] == 0
    assert json.loads((inputs.args.output / "result.json").read_text()) == result


@pytest.mark.parametrize("returncode", [0, 1])
def test_codex_readability_probe_streams_full_paths_and_preserves_stderr(
    native_inputs, monkeypatch, returncode
):
    inputs = native_inputs
    readable = [f"src/{index:04d}-{'x' * 80}.cpp" for index in range(2000)]
    monkeypatch.setattr(worker, "task_readable_files", lambda task: readable)
    inputs.args.output.mkdir()

    def run(command, **kwargs):
        assert command[:4] == ["docker", "exec", "-i", "fixture"]
        assert len(command[-1]) < 1024
        assert len(kwargs["input"]) > 128 * 1024
        assert json.loads(kwargs["input"]) == readable
        return subprocess.CompletedProcess(
            command, returncode, stdout=b"SOURCE_READABLE\n", stderr=b"probe detail\n"
        )

    monkeypatch.setattr(codex.subprocess, "run", run)
    if returncode:
        with pytest.raises(subprocess.CalledProcessError) as raised:
            codex.check_source_readability("fixture", inputs.task, inputs.args.output)
        assert raised.value.stderr == b"probe detail\n"
    else:
        codex.check_source_readability("fixture", inputs.task, inputs.args.output)
    result = json.loads((inputs.args.output / "source-readability.json").read_text())
    assert result == {
        "returncode": returncode,
        "readable_files": 2000,
        "stdout": "SOURCE_READABLE\n",
        "stderr": "probe detail\n",
    }


@pytest.mark.parametrize("agent", ["mini", "codex"])
@pytest.mark.parametrize("failure", ["exit", "spawn"])
def test_scheduler_scores_structured_startup_failure_instead_of_missing_result(
    native_inputs, tmp_path, monkeypatch, agent, failure
):
    inputs = native_inputs
    output = tmp_path / "campaign"
    output.mkdir()
    settings = {
        "task": str(inputs.args.task),
        "qualification": "qualification.json",
        "common_input": str(inputs.args.common_input),
        "mini_source": str(inputs.args.mini_source),
        "agent_seconds": 60,
    }
    (output / "prepared.json").write_text(json.dumps(settings))
    monkeypatch.setattr(
        formal, "PROTOCOL", formal.ROOT / "benchmarks/comparison-full-24-protocol.json"
    )
    monkeypatch.setattr(formal, "ATTEMPT_ID", None)
    monkeypatch.setattr(formal.subprocess, "run", lambda *a, **k: None)
    error_code = "BENCHMARK_STARTUP_FAILED" if failure == "spawn" else "COMMON_TASK_MISMATCH"

    def run(command, log):
        if command[1] == "scripts/score_benchmark_attempt.py":
            worker_result = json.loads((output / agent / "result.json").read_text())
            assert producer_blocker(worker_result) == ("INFRASTRUCTURE_FAILED", "infrastructure")
            target = Path(command[command.index("--output") + 1])
            target.mkdir()
            (target / "score.json").write_text(
                json.dumps(
                    {
                        "status": "INFRASTRUCTURE_FAILED",
                        "accepted": None,
                        "worker_error_code": error_code,
                    }
                )
            )
            return 0
        if failure == "spawn":
            raise FileNotFoundError("native python executable is missing")
        log.write_text(json.dumps({"ok": False, "error_code": error_code}) + "\n")
        return 2

    monkeypatch.setattr(formal, "run", run)
    formal.execute("fmtlib__fmt-1171", output, agent)
    result = json.loads((output / agent / "result.json").read_text())
    summary = json.loads((output / "summary.json").read_text())["attempts"][0]
    assert result["error_code"] == summary["stop_reason"] == error_code
    assert result["usage"]["issued_requests"] == summary["usage"]["issued_requests"] == 0
    assert (
        result["worker_log_sha256"]
        == hashlib.sha256((output / f"{agent}-worker.log").read_bytes()).hexdigest()
    )
    assert summary["score"]["status"] == "INFRASTRUCTURE_FAILED"
    if failure == "spawn":
        assert result["error_type"] == "FileNotFoundError"
        assert result["error_stage"] == "worker_spawn"
        assert result["error_message"] == "native python executable is missing"


@pytest.mark.parametrize(
    "run_id,instance,agent,file_count",
    [
        (41309756321, "actor-framework__actor-framework-2300", "mini", 1162),
        (41309756321, "actor-framework__actor-framework-2300", "codex", 1162),
        (41311415325, "simdjson__simdjson-644", "mini", 1975),
        (41311415325, "simdjson__simdjson-644", "codex", 1975),
    ],
)
def test_original_actions_archives_replay_native_preflight(
    tmp_path, run_id, instance, agent, file_count
):
    mini = os.environ.get("REPROPATCH_NATIVE_STARTUP_MINI")
    evidence = os.environ.get("REPROPATCH_NATIVE_STARTUP_EVIDENCE")
    if not mini or not evidence:
        pytest.skip("原始归档回放需要固定 mini 源码与下载的 Actions 证据目录")
    archive = (
        Path(evidence)
        / str(run_id)
        / "raw/native-startup"
        / f"cross-attempt-{run_id}-{instance}-{agent}"
        / "cross-attempt.tar.gz"
    )
    with tarfile.open(archive) as data:
        inventory = json.load(data.extractfile("archive-manifest.json"))
        manifest = {row["path"]: row for row in inventory["files"]}

        def member(name):
            raw = data.extractfile(name).read()
            assert len(raw) == manifest[name]["size_bytes"]
            assert hashlib.sha256(raw).hexdigest() == manifest[name]["sha256"]
            return raw

        raw_task = json.loads(member("execution-contract/task.yaml"))
        common = member("common-input.json")
        environment = member(f"{agent}-environment/environment.json")
        prepared = member(f"{agent}-environment/preparation.json")
        bundle = member("execution-contract/prepared.bundle")
        original_log = member(f"{agent}-worker.log")
        original_ledger = member(f"ledgers/{agent}.sqlite3")
    assert b"COMMON_TASK_MISMATCH" in original_log
    bundle_path = tmp_path / "prepared.bundle"
    bundle_path.write_bytes(bundle)
    repository = tmp_path / "repository"
    repository.mkdir()
    git(repository, "init", "--template=", "-q")
    git(repository, "fetch", str(bundle_path), raw_task["repository"]["commit"])
    git(repository, "checkout", "--detach", "FETCH_HEAD")
    raw_task["repository"]["path"] = str(repository)
    task = Task.from_dict(raw_task, tmp_path)
    output = tmp_path / "environment"
    output.mkdir()
    source = output / "source"
    source.mkdir()
    preparation.set_container_read_permissions(source)
    (output / "environment.json").write_bytes(environment)
    (output / "preparation.json").write_bytes(prepared)
    common_path = tmp_path / "common-input.json"
    common_path.write_bytes(common)
    ledger_path = tmp_path / "ledger.sqlite3"
    ledger_path.write_bytes(original_ledger)
    ledger = LocalUsageLedger(ledger_path)
    args = SimpleNamespace(
        mini_source=Path(mini),
        mini_environment=output / "environment.json",
        common_input=common_path,
        agent_seconds=60,
    )
    _, initial, _ = worker.mini_inputs(args, task, ledger.policy)
    assert json.loads(initial)["readable"]["file_count"] == file_count
    assert len(worker.task_readable_files(task)) == file_count
    assert common_path.read_bytes() == common
    assert ledger.summary()["issued_requests"] == 0
