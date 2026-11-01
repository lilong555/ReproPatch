"""区分 Docker CLI 启动失败与已执行命令的 125/126/127 退出。"""

import json
import sys
from pathlib import Path

import pytest
from test_process_sandbox import prepare_lifecycle

from repropatch.artifacts import AuditBudget
from repropatch.errors import InfrastructureError
from repropatch.process import CommandResult, RawResult
from repropatch.sandbox import DockerSandbox


@pytest.fixture
def execution(tmp_path, monkeypatch):
    sandbox = DockerSandbox(tmp_path, "repropatch-cpp:0.1")
    history = prepare_lifecycle(sandbox, monkeypatch)
    lifecycle = sandbox._docker
    identifier = "b" * 64
    argv = ("/bin/sh", "-lc", "clang++ --version")
    state = {
        "ID": identifier,
        "ContainerID": "a" * 64,
        "Running": False,
        "Pid": 123,
        "ExitCode": 127,
        "ProcessConfig": {"entrypoint": argv[0], "arguments": list(argv[1:])},
    }
    command = " ".join(argv)
    events = [
        {
            "Type": "container",
            "Action": action,
            "Actor": {
                "ID": "a" * 64,
                "Attributes": {"execID": identifier, "exitCode": "127"},
            },
        }
        for action in (f"exec_create: {command}", f"exec_start: {command}", "exec_die")
    ]
    code = [127]

    def docker(*args, **options):
        if args[0] != "events":
            return lifecycle(*args, **options)
        history.append(args)
        output = "\n".join(json.dumps(item) for item in events)
        return CommandResult(tuple(args), 0, output, 0.001, stdout=output)

    def execute(command, **options):
        stderr = b"/bin/sh: 1: clang++: not found\n" if code[0] else b""
        options["on_data"]("stderr", stderr)
        return RawResult(tuple(command), code[0], b"", stderr, 0.001)

    def inspect(command, **options):
        request = Path(command[3]).read_text()
        assert request.startswith(f"GET /exec/{identifier}/json HTTP/1.1")
        assert command[-2:] == ["system", "dial-stdio"]
        assert options["timeout"] <= 15 and options["output_limit"] == 512 * 1024
        payload = json.dumps(state).encode()
        output = f"HTTP/1.1 200 OK\r\nContent-Length: {len(payload)}\r\n\r\n" + payload.decode()
        return CommandResult(tuple(command), 0, output, 0.001, stdout=output)

    monkeypatch.setattr(sandbox, "_docker", docker)
    monkeypatch.setattr("repropatch.process.run_process_bytes", execute)
    monkeypatch.setattr("repropatch.sandbox.run_process", inspect)
    return sandbox, argv, state, events, code, history


@pytest.mark.parametrize("exit_code", [125, 126, 127])
def test_confirmed_process_exit_allows_next_command(execution, exit_code):
    sandbox, argv, state, events, code, history = execution
    state["ExitCode"] = code[0] = exit_code
    events[-1]["Actor"]["Attributes"]["exitCode"] = str(exit_code)
    with sandbox:
        result = sandbox.run(argv)
        assert result.status == "exited" and result.returncode == exit_code
        assert sandbox.active
        proof = json.loads(
            (sandbox.log_root / f"logs/{result.command_id}/exec-identity.json").read_text()
        )
        assert proof["confirmed"] and proof["exec_id"] == "b" * 64
        assert proof["events"]["size_bytes"] and proof["inspect"]["size_bytes"]
        code[0] = 0
        assert sandbox.run(("/bin/sh", "-lc", "true")).ok
    assert sandbox.cleanup_confirmed
    assert sum(item[0] == "events" for item in history) == 1


@pytest.mark.parametrize("fault", ["missing", "corrupt"])
def test_exec_confirmation_requires_intact_original_logs(execution, monkeypatch, fault):
    sandbox, argv, _, _, _, history = execution
    check = sandbox.exec_start_failed

    def damaged(arguments, result):
        path = sandbox.log_root / result.stderr_log.path
        if fault == "missing":
            path.unlink()
        else:
            path.write_bytes(b"changed")
        return check(arguments, result)

    monkeypatch.setattr(sandbox, "exec_start_failed", damaged)
    with sandbox:
        result = sandbox.run(argv)
        assert result.status == "infra_error" and result.cleanup_confirmed
        assert "ARTIFACT_CORRUPT" in result.error
    assert not any(item[0] == "events" for item in history)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ID", "c" * 64),
        ("ContainerID", "c" * 64),
        ("Running", True),
        ("Pid", 0),
        ("Pid", True),
        ("ExitCode", 126),
        ("ProcessConfig", {"entrypoint": "/missing", "arguments": []}),
    ],
)
def test_unconfirmed_exec_identity_stops_and_cleans(execution, field, value):
    sandbox, argv, state, _, _, _ = execution
    state[field] = value
    with sandbox:
        result = sandbox.run(argv)
        assert result.status == "infra_error"
        assert "CONTAINER_EXEC" in result.error
        assert result.cleanup_confirmed and not sandbox.active
    proof = json.loads(
        (sandbox.log_root / f"logs/{result.command_id}/exec-identity.json").read_text()
    )
    assert not proof["confirmed"] and proof["error"]


@pytest.mark.parametrize("fault", ["missing", "incomplete", "duplicate", "exit-code", "container"])
def test_missing_or_contradictory_exec_events_stop(execution, fault):
    sandbox, argv, _, events, _, _ = execution
    if fault == "missing":
        events.clear()
    elif fault == "incomplete":
        events.pop()
    elif fault == "duplicate":
        extra = json.loads(json.dumps(events[0]))
        extra["Actor"]["Attributes"]["execID"] = "c" * 64
        events.append(extra)
    elif fault == "exit-code":
        events[-1]["Actor"]["Attributes"]["exitCode"] = "126"
    else:
        events[0]["Actor"]["ID"] = "c" * 64
    with sandbox:
        result = sandbox.run(argv)
        assert result.status == "infra_error" and result.cleanup_confirmed


@pytest.mark.parametrize("failure", ["lost", "stopped", "oom", "cleanup"])
def test_container_failure_remains_a_hard_stop(execution, monkeypatch, failure):
    sandbox, argv, _, _, _, _ = execution
    with sandbox:
        inspect = sandbox._inspect
        first = True

        def failed_inspect(*args, **options):
            nonlocal first
            info = inspect(*args, **options)
            if not first:
                return info
            first = False
            if failure == "lost":
                return None
            if failure in {"stopped", "cleanup"}:
                info["State"]["Running"] = False
            else:
                info["State"]["OOMKilled"] = True
            return info

        monkeypatch.setattr(sandbox, "_inspect", failed_inspect)
        if failure == "cleanup":
            close = sandbox.close

            def failed_close():
                raise InfrastructureError("CLEANUP_UNCONFIRMED: 删除失败")

            monkeypatch.setattr(sandbox, "close", failed_close)
        result = sandbox.run(argv)
        if failure == "cleanup":
            assert result.status == "infra_error"
            assert not result.cleanup_confirmed and "CLEANUP_UNCONFIRMED" in result.error
            monkeypatch.setattr(sandbox, "close", close)
        else:
            assert result.status == ("oom_killed" if failure == "oom" else "infra_error")
            assert result.cleanup_confirmed


@pytest.mark.parametrize("mode", ["length", "chunked", "truncated", "error", "large", "timeout"])
def test_exec_inspect_uses_bounded_readonly_cli_transport(tmp_path, mode):
    root = tmp_path / "evidence"
    root.mkdir(mode=0o700)
    # 命令证据目录沿用 run_logged_process 的 0700 权限契约。
    (root / "logs").mkdir(mode=0o700)
    (root / "logs/test").mkdir(mode=0o700)
    sandbox = DockerSandbox(
        tmp_path, "repropatch-cpp:0.1", log_root=root, audit_budget=AuditBudget(root)
    )
    executable = tmp_path / "docker"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json,os,sys,time\n"
        "assert sys.argv[1:] == ['system','dial-stdio']\n"
        "assert 'OPENAI_API_KEY' not in os.environ\n"
        "request=sys.stdin.buffer.read()\n"
        f"assert request == b'GET /exec/{'b' * 64}/json HTTP/1.1\\r\\n"
        "Host: docker\\r\\nConnection: close\\r\\n\\r\\n'\n"
        f"mode={mode!r}\n"
        'body=b\'{"ID":"observed"}\'\n'
        "if mode == 'timeout': time.sleep(10)\n"
        "if mode == 'large': body=b'x'*600000\n"
        "if mode == 'chunked':\n"
        " response=b'HTTP/1.1 200 OK\\r\\nTransfer-Encoding: chunked\\r\\n\\r\\n'"
        "+hex(len(body))[2:].encode()+b'\\r\\n'+body+b'\\r\\n0\\r\\n\\r\\n'\n"
        "else:\n"
        " status='404 Not Found' if mode=='error' else '200 OK'\n"
        " size=len(body)+10 if mode=='truncated' else len(body)\n"
        " response=f'HTTP/1.1 {status}\\r\\nContent-Length: {size}\\r\\n\\r\\n'.encode()+body\n"
        "sys.stdout.buffer.write(response)\n"
    )
    executable.chmod(0o700)
    sandbox.executable = str(executable)
    if mode == "timeout":
        import time

        sandbox.operation_deadline = time.monotonic() + 0.2
    if mode in {"length", "chunked"}:
        info, evidence = sandbox._inspect_exec("b" * 64, "logs/test")
        assert info == {"ID": "observed"}
        assert evidence.read(root, limit=512 * 1024).startswith(b"HTTP/1.1 200")
    else:
        with pytest.raises(InfrastructureError, match="DOCKER_EXEC_INSPECT"):
            sandbox._inspect_exec("b" * 64, "logs/test")
        assert (root / "logs/test/exec-inspect.http").is_file()
