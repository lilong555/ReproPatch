"""Exercise qualification against real compiled regression and clean native oracle."""

import importlib.util
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("qualify_cpp_batch", SCRIPTS / "qualify_cpp_batch.py")
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


@pytest.mark.integration
def test_real_reference_checks_keep_host_and_isolated_qualification_separate(tmp_path, monkeypatch):
    if any(shutil.which(tool) is None for tool in ("cmake", "ninja", "c++")):
        pytest.skip("C++/CMake/Ninja unavailable")
    # The surrounding Git repository catches accidentally applying a nested
    # reference patch in its parent instead of in its intended source tree.
    batch.git(tmp_path, "init", "--template=", "-q", ".")
    source = tmp_path / "upstream"
    (source / "include/fmt").mkdir(parents=True)
    (source / "test").mkdir()
    (source / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.20)\nproject(fmt LANGUAGES CXX)\n"
        "enable_testing()\nadd_subdirectory(test)\n"
    )
    (source / "test/CMakeLists.txt").write_text(
        "function(add_fmt_test name)\n  add_executable(${name} ${name}.cc)\n"
        '  target_include_directories(${name} PRIVATE "${PROJECT_SOURCE_DIR}/include")\n'
        "  add_test(NAME ${name} COMMAND ${name})\nendfunction()\n"
        "add_fmt_test(format-test)\nadd_fmt_test(control-test)\n"
    )
    (source / "include/fmt/value.h").write_text("constexpr int value = 0;\n")
    test = source / "test/format-test.cc"
    test.write_text('#include "fmt/value.h"\nint main() { return value != 0; }\n')
    (source / "test/control-test.cc").write_text("int main() { return 0; }\n")
    batch.git(source, "init", "--template=", "-q", ".")
    batch.git(source, "add", ".")
    batch.git(source, "commit", "-qm", "base")
    base = batch.git(source, "rev-parse", "HEAD").decode().strip()
    test.write_text('#include "fmt/value.h"\nint main() { return value != 1; }\n')
    test_patch = batch.git(source, "diff", "--", "test/").decode()
    batch.git(source, "restore", "test/")
    (source / "include/fmt/value.h").write_text("constexpr int value = 1;\n")
    fix_patch = batch.git(source, "diff", "--", "include/").decode()
    batch.git(source, "restore", "include/")
    record = {
        "instance_id": "fmtlib__fmt-999999",
        "org": "fmtlib",
        "repo": "fmt",
        "base": {"sha": base},
        "fix_patch": fix_patch,
        "test_patch": test_patch,
        "fix_patch_result": {"passed_tests": ["format-test", "control-test"]},
        "resolved_issues": [{"title": "value must be one", "body": ""}],
    }
    args = SimpleNamespace(
        output=tmp_path / "out",
        repository=source,
        backend="native",
        image=None,
        task_timeout=60,
        build_jobs=2,
        keep_builds=False,
        optimization="O0",
    )
    result = batch.qualify(record, args)
    assert result["status"] == "HOST_QUALIFIED"
    assert result["f2p"] == ["format-test"]
    assert result["p2p"] == ["control-test"]
    assert result["phases"]["reference"]["tests"] == {"format-test": "passed"}
    assert result["phases"]["native_oracle"]["tests"] == {
        "format-test": "passed",
        "control-test": "passed",
    }
    assert result["native_oracle"]["adapter_used"] is False
    assert result["task_path"] is None
    assert result["build_retention"] == "release_after_each_phase"
    assert set(result["phase_build_bytes"]) == {"baseline", "reference", "native-oracle"}
    assert all(size > 0 for size in result["phase_build_bytes"].values())
    assert result["build_bytes_before_cleanup"] == 0
    directory = args.output / record["instance_id"]
    assert not list(directory.glob("*-build"))
    assert not (directory / "task.yaml").exists()
    assert (directory / "repository/include/fmt/value.h").read_text().endswith("= 0;\n")
    assert (directory / "manifest.json").is_file()
    # Docker 资格导出的任务同时使用两条独立 CTest 命令，YAML 保持普通值。
    task_path = batch.write_task(
        record,
        directory / "repository",
        directory,
        "sha256:" + "a" * 64,
        result["f2p"],
        result["p2p"],
    )
    exported = batch.Task.load(task_path)
    assert exported.commands.reproduce == exported.commands.verify == tuple(batch.CTEST)
    assert "&id" not in task_path.read_text() and "*id" not in task_path.read_text()

    import check_qualified_cpp_candidate as oracle

    batch.save(
        args.output / "environment.json",
        {
            tool: {"sha256": batch.sha(Path(shutil.which(tool)).resolve())}
            for tool in ("c++", "cmake", "ninja")
        },
    )
    monkeypatch.setattr(oracle, "records", lambda dataset: [record])
    accepted = oracle.check(
        SimpleNamespace(
            output=tmp_path / "oracle-reference",
            qualification=directory / "result.json",
            candidate=directory / "control/reference.patch",
            dataset=tmp_path,
            repository=source,
            timeout=60,
            build_jobs=2,
        )
    )
    assert accepted["status"] == "ORACLE_PASSED"
    assert accepted["accepted"] is True
    assert accepted["oracle"]["tests"] == {"control-test": "passed", "format-test": "passed"}
    arbitrary = tmp_path / "untrusted.patch"
    arbitrary.write_text(fix_patch.replace("= 1", "= 2"))
    rejected = oracle.check(
        SimpleNamespace(
            output=tmp_path / "oracle-rejected",
            qualification=directory / "result.json",
            candidate=arbitrary,
            dataset=tmp_path,
            repository=source,
            timeout=60,
            build_jobs=2,
        )
    )
    assert rejected["status"] == "NATIVE_CANDIDATE_REQUIRES_DOCKER"
    assert rejected["accepted"] is False
    assert "commands" not in rejected


def test_full_native_inventory_cannot_silently_drop_a_required_test(tmp_path, monkeypatch):
    import json
    import time

    runner = batch.Executor("native", None, tmp_path, time.monotonic() + 10, 1)

    def command(argv, source, build, phase, stage):
        if stage == "inventory":
            path = tmp_path / "inventory.json"
            path.write_text(json.dumps({"tests": [{"name": "existing"}]}))
            return {"exit_code": 0, "log": path.name}
        assert stage == "configure"
        return {"exit_code": 0}

    monkeypatch.setattr(runner, "run", command)
    result = runner.suite(tmp_path, "native-oracle", ["existing", "missing"])
    assert result["status"] == "TEST_INVENTORY_MISMATCH"


@pytest.mark.parametrize("cancel", [False, True])
def test_git_preparation_stops_a_stalled_fetch_and_its_child(tmp_path, monkeypatch, cancel):
    """A slow partial-clone helper must not escape the task deadline/cancel."""
    import os
    import threading
    import time

    binary = tmp_path / "git"
    heartbeat = tmp_path / "child-heartbeat"
    child_code = (
        "import os, time\nfrom pathlib import Path\n"
        "for _ in range(80):\n"
        " Path(os.environ['REPROPATCH_TEST_HEARTBEAT']).write_text(str(time.monotonic()))\n"
        " time.sleep(0.05)\n"
    )
    binary.write_text(
        f"#!{sys.executable}\n"
        "import os, subprocess, sys, time\n"
        f"subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
        "time.sleep(4)\n"
    )
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("REPROPATCH_TEST_HEARTBEAT", str(heartbeat))
    timer = threading.Timer(0.5, batch.CANCELLED.set) if cancel else None
    if timer:
        timer.start()
    started = time.monotonic()
    try:
        with pytest.raises(InterruptedError if cancel else TimeoutError):
            batch.git(tmp_path, "archive", "HEAD", deadline=started + (3 if cancel else 0.5))
    finally:
        if timer:
            timer.cancel()
        batch.CANCELLED.clear()
    assert time.monotonic() - started < 2
    # Observe the child itself; /proc may use another PID namespace in CI.
    time.sleep(0.1)
    last_heartbeat = heartbeat.read_text()
    time.sleep(0.2)
    assert heartbeat.read_text() == last_heartbeat
