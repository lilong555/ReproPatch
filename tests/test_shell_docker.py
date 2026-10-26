"""真实 Docker 中验证持久 Shell、写入策略、清理和独立验收。"""

import json
import os
import shlex
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import ROOT, scripted

from repropatch.events import read_events
from repropatch.harness import Harness
from repropatch.models import load_sdk_script
from repropatch.process import run_process
from repropatch.recovery import read_checkpoint, resume_run
from repropatch.repair_sandbox import PersistentRepairSandbox
from repropatch.task import Task, inspect_image
from repropatch.workspace import Worktree

pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(
        os.environ.get("REPROPATCH_DOCKER_TESTS") != "1",
        reason="设置 REPROPATCH_DOCKER_TESTS=1 后运行真实 Docker 验收",
    ),
]

EDIT = (
    "python3 -c \"from pathlib import Path; p=Path('/src/src/stats.cpp'); "
    "p.write_bytes(p.read_bytes().replace(b'int best = 0;', b'int best = samples.front();'))\""
)
BUILD = "cmake -S /src -B /build -DCMAKE_BUILD_TYPE=Debug && cmake --build /build --parallel 2"
CHECK = "ctest --test-dir /build --output-on-failure --no-tests=error"


@pytest.fixture
def shell_task(task):
    raw = task.to_dict()
    image = os.environ.get("REPROPATCH_TEST_IMAGE", "repropatch-cpp:0.1")
    raw["environment"]["image"] = inspect_image(image).image_id
    return Task.from_dict(raw, task.repository.parent)


def bash(command, **arguments):
    return {"tool": "bash", "arguments": {"command": command, **arguments}}


def assert_removed(report):
    resources = json.loads((Path(report["artifact_directory"]) / "resources.json").read_text())
    assert report["cleanup"]["active_code_stopped"]
    for record in resources["containers"]:
        assert record["cleanup_confirmed"] and not record["cleanup_error"]
        check = run_process(["docker", "inspect", record["container_id"]], timeout=10)
        assert check.returncode == 1 and "No such object" in check.stderr
    return resources["containers"]


def tool_results(report):
    return [
        json.loads(p.read_text())
        for p in sorted((Path(report["artifact_directory"]) / "agent/tool-results").glob("*.json"))
    ]


def test_shell_persistent_build_and_independent_cold_oracle(shell_task, tmp_path):
    original = (shell_task.repository / "src/stats.cpp").read_bytes()
    model = scripted(
        [
            bash(
                EDIT
                + " && "
                + BUILD
                + " && "
                + CHECK
                + " && printf persistent > /build/probe"
                + " && stat -c %y /build/CMakeFiles/stats.dir/src/stats.cpp.o > /build/object-time"
            ),
            bash(
                'test "$(cat /build/probe)" = persistent && cmake --build /build && '
                + CHECK
                + ' && test "$(cat /build/object-time)" = '
                + '"$(stat -c %y /build/CMakeFiles/stats.dir/src/stats.cpp.o)"'
                + " && printf incremental-ok"
            ),
            {"finish": "完成"},
        ]
    )
    report = Harness(shell_task, model, tmp_path / "runs", tool_mode="shell-only").run()
    assert report["outcome"] == "ACCEPTED", report
    assert report["candidate_roundtrip_verified"] and report["artifacts_complete"]
    assert report["agent"]["http_attempts"] == 0 and report["usage"]["synthetic"]
    results = tool_results(report)
    assert results[0]["data"]["container_id"] == results[1]["data"]["container_id"]
    assert "incremental-ok" in results[1]["data"]["stdout"]
    containers = assert_removed(report)
    assert len(containers) == 3 and len({c["container_id"] for c in containers}) == 3
    assert sum(c.get("kind") == "repair" for c in containers) == 1
    assert report["baseline"]["compiler_cache"] is None
    assert report["independent"]["compiler_cache"] is None
    assert report["independent"]["cleanup"]["container_id"] != results[0]["data"]["container_id"]
    assert (shell_task.repository / "src/stats.cpp").read_bytes() == original
    model.assert_complete()


def test_shell_readonly_paths_network_and_rename_protection(shell_task, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "host-secret-sentinel")
    probe = """
import errno, os, pathlib, socket
assert os.getuid() == 65534
assert 'OPENAI_API_KEY' not in os.environ
assert not pathlib.Path('/src/.git').exists()
assert not pathlib.Path('/var/run/docker.sock').exists()
for name in ['/src/CMakeLists.txt', '/src/tests/stats_test.cpp', '/src/new.cpp', '/etc/forbidden']:
    try:
        pathlib.Path(name).write_text('modified')
    except OSError as error:
        assert error.errno in (errno.EROFS, errno.EACCES, errno.EPERM)
    else:
        raise AssertionError(name)
try:
    pathlib.Path('/src/src/stats.cpp').unlink()
except OSError:
    pass
else:
    raise AssertionError('source unlink')
connection = socket.socket()
connection.settimeout(1)
assert connection.connect_ex(('1.1.1.1', 53)) != 0
print('isolation-ok')
"""
    model = scripted(
        [
            bash("python3 -c " + shlex.quote(probe)),
            bash(EDIT),
            {"finish": "完成"},
        ]
    )
    report = Harness(shell_task, model, tmp_path / "runs", tool_mode="shell-only").run()
    assert report["outcome"] == "ACCEPTED", report
    assert "isolation-ok" in tool_results(report)[0]["data"]["stdout"]
    assert_removed(report)
    model.assert_complete()


@pytest.mark.parametrize("code", [1, 125, 126, 127])
def test_shell_command_exit_codes_remain_visible_and_recoverable(shell_task, tmp_path, code):
    model = scripted([bash(f"exit {code}"), bash(EDIT), {"finish": "完成"}])
    report = Harness(shell_task, model, tmp_path / "runs", tool_mode="shell-only").run()
    assert report["outcome"] == "ACCEPTED", report
    result = tool_results(report)[0]["data"]
    assert result["exit_code"] == code and result["status"] == "exited"
    assert_removed(report)
    model.assert_complete()


def test_shell_timeout_stops_children_preserves_candidate_and_verifies(shell_task, tmp_path):
    model = scripted(
        [
            bash(EDIT),
            bash("sleep 60 & wait", timeout_seconds=1),
            {"finish": "剩余请求"},
        ]
    )
    report = Harness(shell_task, model, tmp_path / "runs", tool_mode="shell-only").run()
    assert report["outcome"] == "ACCEPTED", report
    assert report["agent"]["agent_stop_reason"] == "SHELL_TIMED_OUT"
    assert len(model.calls) == 2
    assert tool_results(report)[-1]["data"]["status"] == "timed_out"
    assert_removed(report)


def test_shell_output_limit_stops_container_and_preserves_candidate(shell_task, tmp_path):
    from repropatch.process import RAW_OUTPUT_LIMIT

    model = scripted([bash(EDIT), bash("yes feedback"), {"finish": "剩余请求"}])
    report = Harness(shell_task, model, tmp_path / "runs", tool_mode="shell-only").run()
    assert report["outcome"] == "ACCEPTED", report
    assert report["agent"]["agent_stop_reason"] == "SHELL_OUTPUT_LIMIT"
    assert len(model.calls) == 2
    result = tool_results(report)[-1]["data"]
    assert result["status"] == "output_limit"
    assert result["stdout_log"]["size_bytes"] + result["stderr_log"]["size_bytes"] <= (
        RAW_OUTPUT_LIMIT
    )
    assert_removed(report)


def test_shell_model_error_removes_frozen_container(shell_task, tmp_path):
    from agents.testing import ModelStep

    model = scripted([bash(EDIT)])
    model.enqueue(ModelStep(error=RuntimeError("供应商异常详情")))
    report = Harness(shell_task, model, tmp_path / "runs", tool_mode="shell-only").run()
    assert report["outcome"] == "ERROR" and report["reason_code"] == "MODEL_ERROR", report
    assert report["independent"] is None and report["candidate"] is None
    assert "供应商异常详情" not in json.dumps(report, ensure_ascii=False)
    assert_removed(report)
    model.assert_complete()


def test_shell_detached_child_is_rejected_before_next_model_request(shell_task, tmp_path):
    model = scripted([bash("sleep 60 </dev/null >/dev/null 2>&1 &"), bash(EDIT)])
    report = Harness(shell_task, model, tmp_path / "runs", tool_mode="shell-only").run()
    assert report["outcome"] == "ERROR" and report["reason_code"] == "SHELL_PROCESS_LEAK", report
    assert len(model.calls) == 1 and report["candidate"] is None
    assert_removed(report)


def test_shell_invalid_source_bytes_reject_entire_candidate(shell_task, tmp_path):
    original = (shell_task.repository / "src/stats.cpp").read_bytes()
    model = scripted(
        [
            bash(EDIT),
            bash(
                'python3 -c "from pathlib import Path; '
                "Path('/src/src/stats.cpp').write_bytes(b'\\xff')\""
            ),
            {"finish": "剩余请求"},
        ]
    )
    report = Harness(shell_task, model, tmp_path / "runs", tool_mode="shell-only").run()
    assert report["outcome"] == "REJECTED" and report["reason_code"] == "FORBIDDEN_PATCH", report
    assert len(model.calls) == 2 and report["candidate"] is None and report["independent"] is None
    assert (shell_task.repository / "src/stats.cpp").read_bytes() == original
    assert_removed(report)


def test_shell_pause_resume_restores_source_with_fresh_build(shell_task, tmp_path):
    model, source = load_sdk_script(
        ROOT / "examples/models/fix-negative-maximum.shell.json", with_source=True
    )
    harness = Harness(
        replace(shell_task, retain="none"),
        model,
        tmp_path / "runs",
        tool_mode="shell-only",
        pause_after_step=1,
        script_source=source,
    )
    paused = harness.run()
    assert paused["paused"] and paused["artifacts_complete"], paused
    assert len(model.calls) == 1
    checkpoint, _ = read_checkpoint(harness.directory)
    assert checkpoint["counters"] == {"steps_used": 1, "tool_calls_admitted": 1}
    assert_removed(paused)
    resumed = resume_run(harness.directory)
    assert resumed["outcome"] == "ACCEPTED" and resumed["artifacts_complete"], resumed
    assert resumed["agent"]["steps_used"] == 3 and resumed["tool_calls"] == 2
    containers = assert_removed(resumed)
    assert sum(c.get("kind") == "repair" for c in containers) == 2
    next_input = json.loads((harness.directory / "agent/native/0002-input.json").read_text())
    assert any("/build 和 /tmp 已清空" in str(item) for item in next_input["input"])


@pytest.mark.parametrize("boundary", ["checkpoint", "tool_finished"])
def test_shell_controller_death_cleans_persistent_container(shell_task, tmp_path, boundary):
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(shell_task.to_dict()))
    code = """
import os, sys
from pathlib import Path
from repropatch.events import EventLog
from repropatch.harness import Harness
from repropatch.models import load_sdk_script
from repropatch.task import Task
import repropatch.recovery as recovery
boundary = sys.argv[3]
save = recovery.save_checkpoint
def checkpoint(harness, *args):
    result = save(harness, *args)
    if boundary == "checkpoint" and result[0]["step_id"] == 1:
        os._exit(73)
    return result
recovery.save_checkpoint = checkpoint
emit = EventLog.emit
def event(self, kind, *args, **kwargs):
    result = emit(self, kind, *args, **kwargs)
    if boundary == "tool_finished" and kind == "tool_finished":
        os._exit(73)
    return result
EventLog.emit = event
model, source = load_sdk_script(
    Path(sys.argv[1]) / "examples/models/fix-negative-maximum.shell.json", with_source=True
)
Harness(Task.load(Path(sys.argv[2])), model, tool_mode="shell-only", script_source=source).run()
"""
    child = subprocess.run(
        [sys.executable, "-c", code, str(ROOT), str(task_path), boundary],
        capture_output=True,
        timeout=60,
    )
    assert child.returncode == 73, child.stderr.decode()
    (directory,) = shell_task.output_root.iterdir()
    events = read_events(directory, directory.name)
    container = next(
        event["payload"]
        for event in reversed(events.events)
        if event["type"] == "resource_registered" and event["payload"].get("kind") == "repair"
    )
    identifier = container["container_id"]
    try:
        observed = run_process(["docker", "inspect", identifier], timeout=10)
        assert observed.ok and json.loads(observed.stdout)[0]["State"]["Paused"]
        report = resume_run(directory)
        if boundary == "checkpoint":
            assert report["outcome"] == "ACCEPTED" and report["agent"]["steps_used"] == 3, report
        else:
            assert report["outcome"] == "RECOVERY_FAILED", report
            assert report["reason_code"] == "OPEN_AGENT_SEGMENT"
            assert report["agent"]["steps_used"] == 1
        assert_removed(report)
    finally:
        remaining = run_process(["docker", "inspect", identifier], timeout=10)
        if remaining.ok:
            info = json.loads(remaining.stdout)[0]
            assert info["Config"]["Labels"]["repropatch.run"] == directory.name
            run_process(["docker", "rm", "--force", identifier], timeout=10)


def test_shell_cli_example_uses_no_paid_model(shell_task, tmp_path):
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(shell_task.to_dict()))
    child = subprocess.run(
        [
            sys.executable,
            "-m",
            "repropatch",
            "run",
            str(task_path),
            "--engine",
            "fake",
            "--mock-script",
            str(ROOT / "examples/models/fix-negative-maximum.shell.json"),
            "--tool-mode",
            "shell-only",
            "--json",
        ],
        capture_output=True,
        timeout=60,
    )
    assert child.returncode == 0, child.stdout.decode() + child.stderr.decode()
    result = json.loads(child.stdout)
    report = json.loads((Path(result["artifact_directory"]) / "report.json").read_text())
    assert report["outcome"] == "ACCEPTED" and report["benchmark"]["tool_mode"] == "shell-only"
    assert report["usage"]["synthetic"] and report["agent"]["http_attempts"] == 0
    assert_removed(report)


def test_shell_container_is_frozen_between_commands(shell_task, tmp_path):
    with Worktree(shell_task.repository, tmp_path / "work", shell_task.revision) as work:
        source = tmp_path / "source"
        work.export(source)
        with PersistentRepairSandbox(
            source,
            shell_task.environment.image,
            editable=("src/stats.cpp",),
        ) as sandbox:
            assert sandbox.execute("export TEMP_STATE=local; printf retained > /build/probe").ok
            sandbox.assert_idle()
            state = json.loads(
                run_process(["docker", "inspect", sandbox.container_id], timeout=10).stdout
            )[0]["State"]
            assert state["Paused"] and state["Running"]
            assert sandbox.execute(
                'test -z "${TEMP_STATE-}" && test "$(cat /build/probe)" = retained'
            ).ok
            sandbox.assert_idle()
        assert sandbox.cleanup_confirmed
