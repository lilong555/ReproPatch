import os
import sys

import pytest

from repropatch.errors import InfrastructureError
from repropatch.process import CommandResult, run_process
from repropatch.sandbox import DockerSandbox


def test_timeout_and_bounded_output():
    result = run_process(
        [sys.executable, "-c", "import time; print('start', flush=True); time.sleep(9)"],
        timeout=0.2,
    )
    assert result.timed_out and not result.ok
    assert result.duration_seconds < 3
    result = run_process([sys.executable, "-c", "print('x'*1000000)"], output_limit=1024)
    assert result.ok and result.output_truncated and len(result.output) == 1024


def test_background_child_holding_pipe_is_killed():
    result = run_process(
        [sys.executable, "-c", "import os,time; pid=os.fork(); time.sleep(10) if pid==0 else None"],
        timeout=0.2,
    )
    assert result.timed_out and result.duration_seconds < 3


def test_stdin_and_secret_environment_not_inherited(monkeypatch):
    monkeypatch.setenv("REPROPATCH_TEST_SECRET", "should-not-leak")
    result = run_process(
        [
            sys.executable,
            "-c",
            "import os,sys; print(os.environ.get('REPROPATCH_TEST_SECRET')); "
            "print(sys.stdin.read())",
        ]
    )
    assert result.ok and "should-not-leak" not in result.output and "None" in result.output


def test_docker_policy_only_mounts_readonly_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    sandbox = DockerSandbox(tmp_path, "repropatch-cpp:0.1")
    args = sandbox.create_argv()
    for expected in (
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--user=65534:65534",
        "--security-opt=no-new-privileges:true",
        "--pids-limit=64",
        "--memory=768m",
        "--pull=never",
        "--log-driver=none",
    ):
        assert expected in args
    assert args.count("--mount") == 1
    assert args[args.index("--mount") + 1].endswith("target=/src,readonly")
    assert "docker.sock" not in " ".join(args)
    assert "test-secret" not in " ".join(args)
    assert str(os.path.expanduser("~")) not in [a for a in args if a.startswith("type=bind")]


def prepare_lifecycle(sandbox, monkeypatch, *, start_error=False, cleanup_error=False):
    import json

    identifier = "a" * 64
    history = []
    removed = False

    def fake_docker(*args, **kwargs):
        nonlocal removed
        history.append(args)
        if args[0] == "info":
            output = json.dumps(
                dict.fromkeys(("MemoryLimit", "SwapLimit", "CpuCfsQuota", "PidsLimit"), True)
            )
        elif args[0] == "version":
            output = "28.3.2"
        elif args[0] == "image":
            output = json.dumps([{"Id": "sha256:" + "a" * 64, "Config": {}}])
        elif args[0] == "create":
            output = identifier
        elif args[:2] == ("container", "inspect"):
            if removed:
                return None
            output = json.dumps(
                [
                    {
                        "Id": identifier,
                        "Name": "/" + sandbox.name,
                        "Config": {"Labels": sandbox.labels},
                        "State": {"Running": True},
                    }
                ]
            )
        elif args[0] == "start":
            if start_error:
                raise InfrastructureError("original-start-failure")
            output = identifier
        elif args[0] == "rm":
            if cleanup_error:
                raise InfrastructureError("original-rm-failure")
            removed = True
            output = identifier
        else:
            raise AssertionError(args)
        return CommandResult(tuple(args), 0, output, 0.001)

    monkeypatch.setattr(sandbox, "_docker", fake_docker)
    monkeypatch.setattr(sandbox, "_verify_profile", sandbox._verify_owner)
    return history


def test_docker_lifecycle_timeout_cleanup(tmp_path, monkeypatch):
    from repropatch.process import RawResult

    sandbox = DockerSandbox(tmp_path, "repropatch-cpp:0.1")
    history = prepare_lifecycle(sandbox, monkeypatch)

    def timeout(argv, **kwargs):
        kwargs["on_stop"]("timed_out")
        return RawResult(tuple(argv), -9, b"", b"", 0.1, timed_out=True, status="timed_out")

    monkeypatch.setattr("repropatch.process.run_process_bytes", timeout)
    with sandbox:
        result = sandbox.run(("ctest",))
        assert result.timed_out and result.cleanup_confirmed
    assert sum(a[0] == "rm" for a in history) == 1
    assert history[-1] == ("container", "inspect", "a" * 64)


def test_no_docker_never_falls_back(tmp_path, monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr("repropatch.sandbox.run_process", missing)
    with pytest.raises(InfrastructureError, match="no host fallback"):
        with DockerSandbox(tmp_path, "repropatch-cpp:0.1"):
            pytest.fail("must not start")


def test_container_start_error_not_masked_by_cleanup_error(tmp_path, monkeypatch):
    sandbox = DockerSandbox(tmp_path, "repropatch-cpp:0.1")

    prepare_lifecycle(sandbox, monkeypatch, start_error=True, cleanup_error=True)
    with pytest.raises(InfrastructureError, match="original-start-failure") as caught:
        with sandbox:
            pytest.fail("must not start")
    assert "original-rm-failure" in caught.value.__notes__[0]


def test_container_cleanup_preserves_command_failure(tmp_path, monkeypatch):
    sandbox = DockerSandbox(tmp_path, "repropatch-cpp:0.1")

    def failed_cleanup():
        raise InfrastructureError("cleanup-failure")

    monkeypatch.setattr(sandbox, "close", failed_cleanup)
    error = InfrastructureError("command-failure")
    sandbox.__exit__(InfrastructureError, error, None)
    assert str(error) == "command-failure" and "cleanup-failure" in error.__notes__[0]


@pytest.mark.parametrize("image", ["--privileged", "foo bar", "x;sh"])
def test_invalid_image(tmp_path, image):
    with pytest.raises(InfrastructureError):
        DockerSandbox(tmp_path, image)
