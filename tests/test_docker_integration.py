"""Opt-in real isolation checks; absence of a daemon never counts as a pass."""

import os

import pytest

from repropatch.harness import Harness
from repropatch.models import MockModel
from repropatch.process import run_process
from repropatch.sandbox import DockerSandbox

pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(
        os.environ.get("REPROPATCH_DOCKER_TESTS") != "1",
        reason="Set REPROPATCH_DOCKER_TESTS=1 after building the image; real Docker required",
    ),
]


def test_docker_cpp_end_to_end(task, model, tmp_path):
    report = Harness(task, model, tmp_path / "runs").run()
    assert report["status"] == "passed", report
    assert report["isolated"] is True
    assert all(e["image_id"].startswith("sha256:") for e in report["evaluations"])


def test_docker_wrong_patch_is_rejected(task, tmp_path):
    actions = [
        {
            "tool": "edit_file",
            "arguments": {"path": "src/stats.cpp", "old": "int best = 0;", "new": "int best = -1;"},
        },
        {"finish": "done"},
    ]
    report = Harness(task, MockModel(actions), tmp_path / "runs").run()
    assert report["reproduced"] and report["isolated"] is True, report
    assert report["status"] == "failed" and not report["verified"]


def test_real_container_boundary(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "must-stay-on-host")
    source = tmp_path / "source"
    source.mkdir(mode=0o755)
    (source / "sample.txt").write_text("source")
    script = """
import os, pathlib, socket
assert os.getuid() == 65534
assert 'OPENAI_API_KEY' not in os.environ
assert not pathlib.Path('/var/run/docker.sock').exists()
assert not pathlib.Path('/src/.git').exists()
for name in ['/src/sample.txt', '/etc/forbidden']:
    try:
        pathlib.Path(name).write_text('modified')
    except OSError:
        pass
    else:
        raise AssertionError('writable protected path: ' + name)
s = socket.socket()
s.settimeout(1)
assert s.connect_ex(('1.1.1.1', 53)) != 0
pathlib.Path('/build/ok').write_text('build-writable')
print('boundary-ok')
"""
    with DockerSandbox(source, "repropatch-cpp:0.1") as sandbox:
        result = sandbox.run(("python3", "-I", "-c", script))
        assert result.ok and "boundary-ok" in result.output


def test_real_timeout_removes_container(tmp_path):
    source = tmp_path / "source"
    source.mkdir(mode=0o755)
    with DockerSandbox(source, "repropatch-cpp:0.1", timeout=0.5) as sandbox:
        name = sandbox.name
        result = sandbox.run(("python3", "-c", "import time; time.sleep(60)"))
        assert result.timed_out
    assert not run_process(["docker", "inspect", name], timeout=10).ok
