"""异常退出与原始 DuckDB 测试集合的回归覆盖。"""

import importlib
import json
import os
import signal
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
runner = importlib.import_module("native_cpp_runner")
adapter = importlib.import_module("cpp_native_adapter")


def test_native_signal_keeps_exit_code_and_oom_evidence(tmp_path, monkeypatch, capsys):
    snapshots = iter(
        [
            {"memory.events": {"oom": 0, "oom_kill": 0}, "memory.max": 8589934592},
            {
                "memory.events": {"oom": 1, "oom_kill": 1},
                "memory.max": 8589934592,
                "memory.peak": 8589934592,
            },
        ]
    )
    monkeypatch.setattr(runner, "process_resources", lambda: next(snapshots))
    report = tmp_path / "native.log"
    with pytest.raises(RuntimeError, match="exit_code=-15, signal=SIGTERM"):
        runner.execute(
            [sys.executable, "-c", "import signal; signal.raise_signal(signal.SIGTERM)"],
            tmp_path,
            report,
        )
    evidence = json.loads(report.with_suffix(".execution.json").read_text())
    assert evidence["exit_code"] == -signal.SIGTERM
    assert evidence["resource_event_delta"]["memory.events"]["oom_kill"] == 1
    assert evidence["resources_after"]["memory.peak"] == 8589934592
    assert "REPROPATCH_NATIVE_PROCESS_RESULT:" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("cd /testbed ; ./build/test/unittest --reporter junit --out test-results.xml", []),
        (
            'DUCKDB_INSTALL_LIB="$PWD/build/src/libduckdb.so" build/test/unittest "*" '
            "--reporter xml --durations yes --use-colour no --out test-results.xml",
            ["*"],
        ),
        (
            "mkdir -p reports; ./build/test/unittest '*' --reporter junit "
            "--out=reports/all-junit.xml; ./build/test/unittest --list-tests '*' "
            "> reports/all-tests.tsv 2>&1",
            ["*"],
        ),
    ],
)
def test_duckdb_preserves_upstream_full_suite_selector(command, expected):
    assert adapter.duckdb_test_arguments({"native_test_commands": [command]}) == expected


def test_duckdb_rejects_unreviewed_native_filter():
    with pytest.raises(ValueError, match="DUCKDB_NATIVE_ARGUMENTS_REVIEW_REQUIRED"):
        adapter.duckdb_test_arguments(
            {"native_test_commands": ["./build/test/unittest 'test/sql/*' --reporter junit"]}
        )


def test_duckdb_resources_preserve_other_repositories():
    assert adapter.recipe({"org": "duckdb", "repo": "duckdb"})["memory_mib"] == 12288
    assert adapter.recipe({"org": "nlohmann", "repo": "json"})["memory_mib"] == 8192
    assert adapter.recipe({"org": "duckdb", "repo": "duckdb"})["pids_limit"] == 4096
    assert adapter.recipe({"org": "nlohmann", "repo": "json"})["pids_limit"] == 256


def test_caught_resource_failure_is_kept_in_outer_evidence(tmp_path, monkeypatch, capsys):
    snapshots = iter([{"pids.events": {"max": 0}}, {"pids.events": {"max": 1}}])
    monkeypatch.setattr(runner, "process_resources", lambda: next(snapshots))
    code, log = runner.execute(
        [sys.executable, "-c", "print('pthread_create failed'); raise SystemExit(8)"],
        tmp_path,
        tmp_path / "caught.log",
    )
    assert code == 8 and "pthread_create failed" in log
    output = capsys.readouterr().out
    assert "REPROPATCH_NATIVE_PROCESS_RESULT:" in output
    assert json.loads(output.split("REPROPATCH_NATIVE_PROCESS_RESULT: ")[1])[
        "resource_event_delta"
    ] == {"pids.events": {"max": 1}}


def test_qualification_docker_command_reaps_orphans_and_preserves_isolation(tmp_path, monkeypatch):
    batch = importlib.import_module("qualify_cpp_batch")
    recorded = tmp_path / "docker-run.json"
    binary = tmp_path / "docker"
    binary.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\nfrom pathlib import Path\n"
        "if sys.argv[1] == 'run':\n"
        " Path(os.environ['REPROPATCH_DOCKER_INVOCATION']).write_text(json.dumps(sys.argv[1:]))\n"
        " print('native driver completed')\n"
    )
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("REPROPATCH_DOCKER_INVOCATION", str(recorded))
    executor = batch.Executor("docker", "sha256:" + "a" * 64, tmp_path, time.monotonic() + 10, 2)
    try:
        result = executor.run(["ctest"], tmp_path, tmp_path / "build", "baseline", "ctest")
        argv = json.loads(recorded.read_text())
        assert result["exit_code"] == 0
        assert argv.count("--init") == 1
        assert {"--network=none", "--read-only", "--cap-drop=ALL", "--pids-limit=256"} <= set(argv)
    finally:
        executor.build_root.rmdir()
